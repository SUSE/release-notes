# NVIDIA Kernel Patches GitLab Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate the bi-weekly extraction of NVIDIA kernel patches from the internal SUSE `kernel-source` repository and their publication to `SUSE/release-notes` via GitLab CI.

**Architecture:** A scheduled GitLab CI pipeline on `gitlab.suse.de` pulls changes from `git://kerncvs.suse.de/kernel-source.git` using blobless/incremental fetches. An enhanced Python script diffs `series.conf` and extracts patch metadata (commit SHA, upstream version, references, subject) into an AsciiDoc document `adoc/sles/16.1/nvidia-patches.adoc`. If changes occur, the CI pipeline creates a Git branch and opens a Pull Request against `SUSE/release-notes` on GitHub.

**Tech Stack:** Python 3 (standard library, `pytest`), Git, GitLab CI, GitHub REST API / CLI (`gh`), AsciiDoc / DAPS.

## Global Constraints

- Kernel source repo URL: `git://kerncvs.suse.de/kernel-source.git`.
- Release branches: `SL-16.1-NV` compared against `origin/SL-16.1`.
- AsciiDoc style: One sentence per line; ASD-STE100 Simplified Technical English.
- Commit message format: `<Product> <Version>: <imperative subject> (<issue-id>)`.
- Release notes target path: `adoc/sles/16.1/nvidia-patches.adoc`.

---

### Task 1: Enhance `scripts/fetch-nvidia-kernel-patches.py` with Metadata Extraction and Formats

**Files:**
- Modify: `scripts/fetch-nvidia-kernel-patches.py`
- Test: `tests/test_fetch_nvidia_kernel_patches.py`

**Interfaces:**
- Consumes: Patch files inside `patches.suse/` and `series.conf` diff from Git.
- Produces: Structured dictionary of patch metadata (`patch`, `commit`, `upstream_version`, `references`, `subject`) and formatters for AsciiDoc table and plain text.

- [ ] **Step 1: Write unit tests for patch metadata extraction and AsciiDoc formatting**

```python
# tests/test_fetch_nvidia_kernel_patches.py
import pytest
from unittest.mock import patch, mock_open
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import fetch_nvidia_kernel_patches as fnp

SAMPLE_PATCH_CONTENT = """From: Dev <dev@suse.com>
Date: Wed, 1 Jan 2026 00:00:00 +0000
Subject: [PATCH] soc/tegra: fuse: Register nvmem lookups at probe
Git-commit: 0bbff9ed81654d5f06bfca484681756ee407f924
Patch-mainline: v6.13-rc1
References: jsc#NVIDIA-55 bsc#1272627

This patch registers nvmem lookups at probe.
"""

def test_extract_patch_metadata():
    with patch("builtins.open", mock_open(read_data=SAMPLE_PATCH_CONTENT)):
        meta = fnp.extract_patch_metadata("patches.suse/sample.patch")
        assert meta["patch"] == "patches.suse/sample.patch"
        assert meta["commit"] == "0bbff9ed81654d5f06bfca484681756ee407f924"
        assert meta["upstream"] == "v6.13-rc1"
        assert meta["references"] == "jsc#NVIDIA-55 bsc#1272627"
        assert meta["subject"] == "soc/tegra: fuse: Register nvmem lookups at probe"

def test_format_asciidoc_table():
    patches = [
        {
            "patch": "patches.suse/sample.patch",
            "commit": "0bbff9ed81654d5f06bfca484681756ee407f924",
            "upstream": "v6.13-rc1",
            "references": "jsc#NVIDIA-55",
            "subject": "soc/tegra: fuse: Register nvmem lookups at probe",
        }
    ]
    adoc = fnp.format_asciidoc(patches)
    assert "[cols=\"2,2,3,5\", options=\"header\"]" in adoc
    assert "| Commit | Upstream | Reference | Subject" in adoc
    assert "`0bbff9ed8165`" in adoc
    assert "jsc#NVIDIA-55" in adoc
    assert "soc/tegra: fuse: Register nvmem lookups at probe" in adoc
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fetch_nvidia_kernel_patches.py -v`
Expected: FAIL (modules / functions not defined or different signatures)

- [ ] **Step 3: Implement extraction and formatting functions**

Update `scripts/fetch-nvidia-kernel-patches.py`:
```python
#!/usr/bin/env python3
"""
fetch-nvidia-kernel-patches.py

Extracts NVIDIA kernel patches from series.conf and patches.suse/ headers.
Supports output in AsciiDoc, plain text, and JSON formats.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def git(*args, cwd=None):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )


def extract_header(lines, tag):
    """Extract words following the first occurrence of tag (case-insensitive)."""
    for line in lines:
        if line.lower().startswith(tag.lower()):
            parts = line.split(None, 1)
            return parts[1].strip() if len(parts) > 1 else ""
    return ""


def clean_subject(subj):
    """Strip [PATCH ...] prefix and clean up whitespace."""
    subj = re.sub(r"^\[PATCH[^\]]*\]\s*", "", subj, flags=re.IGNORECASE)
    return " ".join(subj.split())


def extract_patch_metadata(patch_path):
    """Parse patch file and extract commit, upstream version, references, and subject."""
    try:
        with open(patch_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(120)]
    except OSError:
        lines = []

    commit = extract_header(lines, "Git-commit:")
    upstream = extract_header(lines, "Patch-mainline:")
    references = extract_header(lines, "References:")
    subject = clean_subject(extract_header(lines, "Subject:"))

    return {
        "patch": str(patch_path),
        "commit": commit,
        "upstream": upstream,
        "references": references,
        "subject": subject,
    }


def format_asciidoc(patches):
    """Render patches as an AsciiDoc table."""
    lines = [
        "// Automatically generated by scripts/fetch-nvidia-kernel-patches.py. Do not edit manually.",
        "[cols=\"2,2,3,5\", options=\"header\"]",
        "|===",
        "| Commit | Upstream | Reference | Subject",
    ]
    for p in patches:
        short_commit = f"`{p['commit'][:12]}`" if p["commit"] else "-"
        upstream = p["upstream"] if p["upstream"] else "-"
        refs = p["references"] if p["references"] else "-"
        subj = p["subject"].replace("|", "\\|") if p["subject"] else "-"
        lines.append(f"| {short_commit} | {upstream} | {refs} | {subj}")
    lines.append("|===")
    return "\n".join(lines) + "\n"


def format_text(patches):
    """Render patches as aligned text."""
    lines = []
    for p in patches:
        commit = p["commit"][:12] if p["commit"] else "-"
        upstream = p["upstream"] if p["upstream"] else "-"
        refs = p["references"] if p["references"] else "-"
        lines.append(f"{commit:<14} {upstream:<10} {refs:<20} {p['subject']}")
    return "\n".join(lines) + "\n"


def get_series_patches(repo_path, base_rev, target_rev=None):
    """Get list of patch files added to series.conf between base_rev and target_rev."""
    rev_arg = f"{base_rev}..{target_rev}" if target_rev else base_rev
    diff = git("diff", rev_arg, "--", "series.conf", cwd=repo_path).stdout
    patches = [
        line[1:].strip()
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++") and "#" not in line and len(line.strip()) > 5
    ]
    return patches


def main():
    parser = argparse.ArgumentParser(description="Extract NVIDIA kernel patches from kernel-source.")
    parser.add_argument("base_rev", nargs="?", default="origin/SL-16.1", help="Base Git revision (default: origin/SL-16.1)")
    parser.add_argument("target_rev", nargs="?", default=None, help="Target Git revision (optional)")
    parser.add_argument("--repo-dir", default=".", help="Path to kernel-source repository checkout")
    parser.add_argument("--format", choices=["asciidoc", "text", "json"], default="text", help="Output format")
    parser.add_argument("-o", "--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    repo = Path(args.repo_dir)
    patch_names = get_series_patches(repo, args.base_rev, args.target_rev)

    records = []
    for name in patch_names:
        patch_file = repo / name
        records.append(extract_patch_metadata(patch_file))

    if args.format == "asciidoc":
        output = format_asciidoc(records)
    elif args.format == "json":
        output = json.dumps(records, indent=2)
    else:
        output = format_text(records)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fetch_nvidia_kernel_patches.py -v`
Expected: PASS

- [ ] **Step 5: Test against local `~/work/git/kernel-source`**

Run: `python3 scripts/fetch-nvidia-kernel-patches.py --repo-dir /home/lukas/work/git/kernel-source origin/SL-16.1 --format text | head -n 10`
Expected: 10 lines of parsed patches with commit, upstream, references, and subject.

- [ ] **Step 6: Commit changes**

```bash
git add scripts/fetch-nvidia-kernel-patches.py tests/test_fetch_nvidia_kernel_patches.py
git commit -m "scripts: enhance fetch-nvidia-kernel-patches with metadata extraction and formats"
```

---

### Task 2: Create AsciiDoc Patch Document and Link from SLES 16.1 Release Notes

**Files:**
- Create: `adoc/sles/16.1/nvidia-patches.adoc`
- Modify: `adoc/sles/version161.adoc`

**Interfaces:**
- Consumes: AsciiDoc formatted table from `fetch-nvidia-kernel-patches.py`.
- Produces: Rendered release notes section with link to NVIDIA patches list.

- [ ] **Step 1: Create `adoc/sles/16.1/nvidia-patches.adoc` template**

Create `adoc/sles/16.1/nvidia-patches.adoc`:
```asciidoc
[#sec-nvidia-kernel-patches]
= NVIDIA Kernel Patches in {productname} {this-version}

This document lists kernel patches included in {productname} {this-version} specifically for NVIDIA platforms and hardware enablement.
These patches originate from the `{nvidia}` kernel enablement branch and supplement the baseline enterprise kernel.

include::nvidia-patches-table.adoc[]
```

- [ ] **Step 2: Generate initial `adoc/sles/16.1/nvidia-patches-table.adoc` from `kernel-source`**

Run: `python3 scripts/fetch-nvidia-kernel-patches.py --repo-dir /home/lukas/work/git/kernel-source origin/SL-16.1 --format asciidoc -o adoc/sles/16.1/nvidia-patches-table.adoc`
Expected: Valid AsciiDoc table file created with 200+ patch entries.

- [ ] **Step 3: Link patch document in `adoc/sles/version161.adoc`**

Add link in `adoc/sles/version161.adoc` under `== {arm}-specific changes ({aarch64})`:
```asciidoc
[#jsc-NVIDIA-patches-161]
=== NVIDIA platform kernel enablement patches

{productname} {this-version} incorporates platform enablement and performance patches for {nvidia} Grace and Tegra hardware.
For the complete list of included patches, upstream commits, and issue references, refer to the link:nvidia-patches.html[NVIDIA Kernel Patches List].
```

- [ ] **Step 4: Validate Release Notes build**

Run: `make validate PRODUCT_VERSION=sles_16.1`
Expected: Validation succeeds without syntax or ID errors.

- [ ] **Step 5: Commit changes**

```bash
git add adoc/sles/16.1/nvidia-patches.adoc adoc/sles/16.1/nvidia-patches-table.adoc adoc/sles/version161.adoc
git commit -m "SLES 16.1: Add reference and list for NVIDIA kernel patches"
```

---

### Task 3: Create GitLab CI Automation Script and Pipeline Configuration

**Files:**
- Create: `scripts/sync-nvidia-patches.sh`
- Create: `.gitlab-ci.nvidia-sync.yml` (template for `gitlab.suse.de`)
- Test: `tests/test_sync_script.sh`

**Interfaces:**
- Consumes: `GIT_TOKEN` (GitHub Personal Access Token or App Token), `git://kerncvs.suse.de/kernel-source.git`.
- Produces: Git branch `update-nvidia-patches-<date>` and GitHub Pull Request against `SUSE/release-notes:main`.

- [ ] **Step 1: Write `scripts/sync-nvidia-patches.sh`**

Create `scripts/sync-nvidia-patches.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

# sync-nvidia-patches.sh
# Fetches kernel-source, regenerates nvidia-patches-table.adoc, and opens a GitHub PR if changed.

KERNEL_REPO_URL="${KERNEL_REPO_URL:-git://kerncvs.suse.de/kernel-source.git}"
KERNEL_DIR="${KERNEL_DIR:-/tmp/kernel-source}"
BASE_BRANCH="${BASE_BRANCH:-origin/SL-16.1}"
TARGET_BRANCH="${TARGET_BRANCH:-SL-16.1-NV}"
OUTPUT_ADOC="adoc/sles/16.1/nvidia-patches-table.adoc"
DATE_TAG="$(date +%Y%m%d)"
SYNC_BRANCH="update-nvidia-patches-${DATE_TAG}"

echo "==> Fetching kernel-source from ${KERNEL_REPO_URL}..."
if [ ! -d "${KERNEL_DIR}/.git" ]; then
    mkdir -p "${KERNEL_DIR}"
    git clone --filter=blob:none --no-checkout "${KERNEL_REPO_URL}" "${KERNEL_DIR}"
fi

git -C "${KERNEL_DIR}" fetch --depth 1 origin "${BASE_BRANCH##origin/}"
git -C "${KERNEL_DIR}" fetch --depth 1 origin "${TARGET_BRANCH}"
git -C "${KERNEL_DIR}" checkout -f "origin/${TARGET_BRANCH}"

echo "==> Extracting patches..."
python3 scripts/fetch-nvidia-kernel-patches.py \
    --repo-dir "${KERNEL_DIR}" \
    "${BASE_BRANCH}" \
    --format asciidoc \
    -o "${OUTPUT_ADOC}"

echo "==> Checking for documentation changes..."
if git diff --quiet "${OUTPUT_ADOC}"; then
    echo "No changes in NVIDIA kernel patch list. Exiting."
    exit 0
fi

echo "==> Changes detected in ${OUTPUT_ADOC}."
if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "Notice: GITHUB_TOKEN is not set. Updated ${OUTPUT_ADOC} locally without opening PR."
    exit 0
fi

git checkout -B "${SYNC_BRANCH}"
git add "${OUTPUT_ADOC}"
git commit -m "SLES 16.1: Update NVIDIA kernel patches list (${DATE_TAG})"
git push -u "https://x-access-token:${GITHUB_TOKEN}@github.com/SUSE/release-notes.git" "${SYNC_BRANCH}" --force

echo "==> Opening GitHub Pull Request..."
curl -s -X POST \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    https://api.github.com/repos/SUSE/release-notes/pulls \
    -d "{
        \"title\": \"SLES 16.1: Update NVIDIA kernel patches list (${DATE_TAG})\",
        \"head\": \"${SYNC_BRANCH}\",
        \"base\": \"main\",
        \"body\": \"Automated bi-weekly update of NVIDIA kernel patches from ${TARGET_BRANCH}.\"
    }"
echo "==> Pull Request created successfully."
```

- [ ] **Step 2: Make script executable**

Run: `chmod +x scripts/sync-nvidia-patches.sh`

- [ ] **Step 3: Write `.gitlab-ci.nvidia-sync.yml` template**

Create `.gitlab-ci.nvidia-sync.yml`:
```yaml
# GitLab CI schedule pipeline configuration for gitlab.suse.de
stages:
  - sync

sync-nvidia-patches:
  stage: sync
  image: registry.opensuse.org/opensuse/tumbleweed:latest
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - if: $CI_PIPELINE_SOURCE == "web"
  before_script:
    - zypper -n install git curl python3
    - git config --global user.name "SUSE Release Notes Bot"
    - git config --global user.email "doc-team@suse.com"
  script:
    - ./scripts/sync-nvidia-patches.sh
  cache:
    key: kernel-source-cache
    paths:
      - /tmp/kernel-source
```

- [ ] **Step 4: Verify script dry-run locally**

Run: `GITHUB_TOKEN="" KERNEL_DIR="/home/lukas/work/git/kernel-source" ./scripts/sync-nvidia-patches.sh`
Expected: Runs extraction, updates `adoc/sles/16.1/nvidia-patches-table.adoc`, and exits cleanly.

- [ ] **Step 5: Commit changes**

```bash
git add scripts/sync-nvidia-patches.sh .gitlab-ci.nvidia-sync.yml
git commit -m "scripts: add sync-nvidia-patches automation script and GitLab CI config"
```

---

### Task 4: Docserv Deliverable Verification & Documentation

**Files:**
- Modify: `docs/nvidia-patches-workflow.md`

- [ ] **Step 1: Document GitLab CI setup and secret configuration**

Update `docs/nvidia-patches-workflow.md` with:
- Instructions for creating the project on `gitlab.suse.de`.
- Setting up the CI schedule (every 14 days).
- Adding `GITHUB_TOKEN` secret in GitLab CI/CD Variables with repository write/PR permissions.
- Verifying the DAPS build on docserv.

- [ ] **Step 2: Commit documentation update**

```bash
git add docs/nvidia-patches-workflow.md
git commit -m "docs: add GitLab CI schedule and secret configuration instructions"
```
