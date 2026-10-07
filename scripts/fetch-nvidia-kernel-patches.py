#!/usr/bin/env python3
"""
fetch-nvidia-kernel-patches.py

Clones or updates the kernel-source branch SL-16.1-NV from kerncvs.suse.de,
inspects patches.suse/ for patches referencing 'linux-nvidia-6.18' (or another pattern),
and compiles an ordered list into a text, detailed, AsciiDoc, Markdown, or JSON file.

Usage:
    ./fetch-nvidia-kernel-patches.py [options]

Examples:
    ./fetch-nvidia-kernel-patches.py
    ./fetch-nvidia-kernel-patches.py --format detailed -o patches-detailed.txt
    ./fetch-nvidia-kernel-patches.py --format adoc -o patches.adoc
    ./fetch-nvidia-kernel-patches.py --repo-dir /path/to/existing/kernel-source
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys

DEFAULT_REMOTE = "git://kerncvs.suse.de/kernel-source.git"
DEFAULT_BRANCH = "SL-16.1-NV"
DEFAULT_REF_PATTERN = "linux-nvidia-6.18"
DEFAULT_CACHE_DIR = os.path.expanduser("~/.cache/kernel-source-nv")
DEFAULT_OUTPUT_FILE = "nvidia-kernel-patches.txt"


def update_or_clone_repo(remote: str, branch: str, cache_dir: str, no_fetch: bool = False):
    """Ensure the kernel-source repo is cloned and up to date."""
    if not os.path.exists(cache_dir):
        print(f"[*] Cloning {remote} ({branch}) to {cache_dir}...", file=sys.stderr)
        os.makedirs(os.path.dirname(os.path.abspath(cache_dir)), exist_ok=True)
        cmd = [
            "git", "clone",
            "--depth", "1",
            "--branch", branch,
            "--single-branch",
            remote,
            cache_dir,
        ]
        res = subprocess.run(cmd, check=False)
        if res.returncode != 0:
            sys.exit(f"Error: git clone failed with code {res.returncode}")
    elif not no_fetch:
        print(f"[*] Fetching latest updates for {branch} in {cache_dir}...", file=sys.stderr)
        cmd_fetch = ["git", "-C", cache_dir, "fetch", "--depth", "1", "origin", branch]
        res = subprocess.run(cmd_fetch, check=False)
        if res.returncode != 0:
            print(f"Warning: git fetch failed. Using existing local files.", file=sys.stderr)
        else:
            cmd_reset = ["git", "-C", cache_dir, "reset", "--hard", "FETCH_HEAD"]
            subprocess.run(cmd_reset, check=False)


def parse_series_conf(repo_dir: str):
    """Return dictionary mapping patch filename to its 0-based index in series.conf."""
    series_file = os.path.join(repo_dir, "series.conf")
    order = {}
    if not os.path.isfile(series_file):
        return order

    with open(series_file, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f):
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            for part in line_str.split():
                if part.endswith(".patch"):
                    fname = os.path.basename(part)
                    if fname not in order:
                        order[fname] = idx
    return order


def extract_patches(repo_dir: str, ref_pattern: str, series_order: dict):
    """Find patches referencing ref_pattern and parse their metadata."""
    patches_dir = os.path.join(repo_dir, "patches.suse")
    if not os.path.isdir(patches_dir):
        sys.exit(f"Error: patches directory not found at {patches_dir}")

    results = []
    pattern_re = re.compile(rf"\b{re.escape(ref_pattern)}\b", re.IGNORECASE)

    for entry in sorted(os.scandir(patches_dir), key=lambda e: e.name):
        if not entry.name.endswith(".patch") or not entry.is_file():
            continue

        try:
            with open(entry.path, "r", encoding="utf-8", errors="ignore") as f:
                header = f.read(8192)
        except OSError as e:
            print(f"Warning: could not read {entry.path}: {e}", file=sys.stderr)
            continue

        if not pattern_re.search(header):
            continue

        lines = header.splitlines()
        subject = ""
        references = ""
        git_commit = ""
        patch_mainline = ""
        author = ""

        for i, line in enumerate(lines):
            if line.startswith("Subject:"):
                subj_parts = [re.sub(r"^Subject:\s*(\[[^\]]*\]\s*)?", "", line)]
                j = i + 1
                while j < len(lines) and (lines[j].startswith(" ") or lines[j].startswith("\t")):
                    subj_parts.append(lines[j].strip())
                    j += 1
                subject = " ".join(subj_parts)
            elif line.startswith("From:") and not author:
                author = line.replace("From:", "").strip()
            elif line.startswith("References:"):
                references = line.replace("References:", "").strip()
            elif line.startswith("Git-commit:"):
                git_commit = line.replace("Git-commit:", "").strip()
            elif line.startswith("Patch-mainline:"):
                patch_mainline = line.replace("Patch-mainline:", "").strip()

        extra_refs = [r for r in references.split() if not pattern_re.search(r)]

        results.append({
            "filename": entry.name,
            "subject": subject,
            "author": author,
            "mainline": patch_mainline,
            "git_commit": git_commit,
            "references": references,
            "extra_references": extra_refs,
            "order": series_order.get(entry.name, 999999),
        })

    return results


def format_plain(patches):
    return "\n".join(p["filename"] for p in patches) + "\n"


def format_detailed(patches):
    lines = []
    for i, p in enumerate(patches, 1):
        lines.append(f"{i:2d}. {p['filename']}")
        if p["subject"]:
            lines.append(f"    Subject:  {p['subject']}")
        if p["mainline"]:
            lines.append(f"    Mainline: {p['mainline']}")
        if p["git_commit"]:
            lines.append(f"    Commit:   {p['git_commit']}")
        if p["extra_references"]:
            lines.append(f"    Refs:     {' '.join(p['extra_references'])}")
        lines.append("")
    return "\n".join(lines)


def format_adoc(patches):
    lines = [
        "// List of NVIDIA kernel patches referencing linux-nvidia-6.18",
        "",
    ]
    for p in patches:
        subj = p["subject"] if p["subject"] else p["filename"]
        extra = []
        if p["mainline"]:
            extra.append(f"Mainline: {p['mainline']}")
        if p["git_commit"]:
            extra.append(f"Commit: {p['git_commit'][:12]}")
        if p["extra_references"]:
            extra.append(f"Refs: {', '.join(p['extra_references'])}")

        suffix = f" ({'; '.join(extra)})" if extra else ""
        lines.append(f"* `{p['filename']}`: {subj}{suffix}")
    lines.append("")
    return "\n".join(lines)


def format_markdown(patches):
    lines = ["# NVIDIA Kernel Patches", ""]
    for i, p in enumerate(patches, 1):
        subj = p["subject"] if p["subject"] else p["filename"]
        extra = []
        if p["mainline"]:
            extra.append(f"Mainline: `{p['mainline']}`")
        if p["git_commit"]:
            extra.append(f"Commit: `{p['git_commit'][:12]}`")
        if p["extra_references"]:
            extra.append(f"Refs: {', '.join(p['extra_references'])}")

        meta = f" - *{', '.join(extra)}*" if extra else ""
        lines.append(f"{i}. `{p['filename']}` - {subj}{meta}")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Compile a list of NVIDIA kernel patches from kernel-source."
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output file path, or '-' for stdout (default: {DEFAULT_OUTPUT_FILE})",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["plain", "detailed", "adoc", "markdown", "json"],
        default="plain",
        help="Output format: plain, detailed, adoc, markdown, json (default: plain)",
    )
    parser.add_argument(
        "--repo-dir",
        default=None,
        help="Path to existing kernel-source checkout (skips git clone if provided)",
    )
    parser.add_argument(
        "--cache-dir",
        default=DEFAULT_CACHE_DIR,
        help=f"Directory to store/cache kernel-source clone (default: {DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--remote",
        default=DEFAULT_REMOTE,
        help=f"Remote git URL (default: {DEFAULT_REMOTE})",
    )
    parser.add_argument(
        "--branch",
        default=DEFAULT_BRANCH,
        help=f"Remote git branch (default: {DEFAULT_BRANCH})",
    )
    parser.add_argument(
        "--reference",
        default=DEFAULT_REF_PATTERN,
        help=f"Reference string to search for (default: {DEFAULT_REF_PATTERN})",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Do not fetch git updates from remote (use local cached files)",
    )
    parser.add_argument(
        "--sort",
        choices=["series", "alpha"],
        default="series",
        help="Sort patches by series.conf application order or alphabetically (default: series)",
    )

    args = parser.parse_args()

    repo_dir = args.repo_dir
    if not repo_dir:
        repo_dir = args.cache_dir
        update_or_clone_repo(
            remote=args.remote,
            branch=args.branch,
            cache_dir=repo_dir,
            no_fetch=args.no_fetch,
        )

    series_order = parse_series_conf(repo_dir)
    patches = extract_patches(repo_dir, args.reference, series_order)

    if args.sort == "series":
        patches.sort(key=lambda x: x["order"])
    elif args.sort == "alpha":
        patches.sort(key=lambda x: x["filename"])

    if args.format == "plain":
        content = format_plain(patches)
    elif args.format == "detailed":
        content = format_detailed(patches)
    elif args.format == "adoc":
        content = format_adoc(patches)
    elif args.format == "markdown":
        content = format_markdown(patches)
    elif args.format == "json":
        content = json.dumps(patches, indent=2) + "\n"

    if args.output == "-":
        sys.stdout.write(content)
    else:
        out_path = os.path.abspath(args.output)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(
            f"[*] Successfully wrote {len(patches)} patches to {out_path} (format: {args.format})",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
