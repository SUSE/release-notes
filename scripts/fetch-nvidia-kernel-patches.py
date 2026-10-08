#!/usr/bin/env python3
"""
fetch-nvidia-kernel-patches.py

Extracts NVIDIA kernel patches from series.conf and patch headers.
Supports fetching directly over HTTPS via kerncvs Gitweb (fast, no git clone),
or reading from a local kernel-source checkout.
Outputs in AsciiDoc, plain text, and JSON formats.
"""

import argparse
import concurrent.futures
import difflib
import json
import re
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
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
    """Extract header value from patch text lines, supporting RFC 822 continuation lines."""
    result = []
    capturing = False
    for line in lines:
        sline = line.lstrip()
        if sline.lower().startswith(tag.lower()):
            parts = sline.split(None, 1)
            if len(parts) > 1:
                result.append(parts[1].strip())
            capturing = True
        elif capturing:
            if re.match(r"^[A-Za-z0-9_-]+:\s*", sline):
                break
            if line.startswith((" ", "\t")):
                result.append(sline.strip())
            else:
                break
    return " ".join(result)


def clean_subject(subj):
    """Strip [PATCH ...] prefix and clean up whitespace."""
    subj = re.sub(r"^\[PATCH[^\]]*\]\s*", "", subj, flags=re.IGNORECASE)
    return " ".join(subj.split())


def extract_patch_metadata(patch_path):
    """Parse local patch file and extract commit, upstream version, references, and subject."""
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


def fetch_http_url(url, range_bytes=None, timeout=15):
    """Fetch URL contents with SSL fallback and optional HTTP range header."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; SUSE-Release-Notes/1.0)")
    if range_bytes:
        req.add_header("Range", f"bytes={range_bytes}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        try:
            unverified_ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=unverified_ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return ""


def get_series_patches_http(gitweb_url, base_ref, target_ref):
    """Fetch series.conf for base and target over HTTPS and compute added patches."""
    base = base_ref.replace("origin/", "").strip()
    target = target_ref.replace("origin/", "").strip()
    base_url = f"{gitweb_url};a=blob_plain;f=series.conf;hb=refs/heads/{base}"
    target_url = f"{gitweb_url};a=blob_plain;f=series.conf;hb=refs/heads/{target}"

    base_content = fetch_http_url(base_url)
    target_content = fetch_http_url(target_url)

    if not base_content or not target_content:
        raise RuntimeError(f"Failed to fetch series.conf for {base} or {target} from {gitweb_url}")

    base_lines = base_content.splitlines(keepends=True)
    target_lines = target_content.splitlines(keepends=True)

    diff = list(difflib.unified_diff(base_lines, target_lines))
    patches = []
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            clean = line[1:].split("#")[0].strip()
            if clean and len(clean) > 5:
                patches.append(clean)
    return patches


def fetch_patch_metadata_http(gitweb_url, target_ref, patch_name):
    """Fetch patch header over HTTPS and extract metadata."""
    target = target_ref.replace("origin/", "").strip()
    quoted_name = urllib.parse.quote(patch_name)
    url = f"{gitweb_url};a=blob_plain;f={quoted_name};hb=refs/heads/{target}"
    content = fetch_http_url(url, range_bytes="0-4096", timeout=10)
    lines = content.splitlines()[:120]

    commit = extract_header(lines, "Git-commit:")
    upstream = extract_header(lines, "Patch-mainline:")
    references = extract_header(lines, "References:")
    subject = clean_subject(extract_header(lines, "Subject:"))

    return {
        "patch": patch_name,
        "commit": commit,
        "upstream": upstream,
        "references": references,
        "subject": subject,
    }


def format_asciidoc(patches):
    """Render patches as an AsciiDoc table."""
    lines = [
        "// Automatically generated by scripts/fetch-nvidia-kernel-patches.py. Do not edit manually.",
        '[cols="2,2,3,5", options="header"]',
        "|===",
        "| Commit | Upstream | Reference | Subject",
    ]
    for p in patches:
        short_commit = f"`{p['commit'][:12]}`" if p["commit"] else "-"
        upstream = p["upstream"].replace("|", "\\|") if p["upstream"] else "-"
        refs = p["references"].replace("|", "\\|") if p["references"] else "-"
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
    """Get list of patch files added to series.conf between base_rev and target_rev from local repo."""
    rev_arg = f"{base_rev}..{target_rev}" if target_rev else base_rev
    diff = git("diff", rev_arg, "--", "series.conf", cwd=repo_path).stdout
    patches = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            clean_line = line[1:].split("#")[0].strip()
            if clean_line and len(clean_line) > 5:
                patches.append(clean_line)
    return patches


def main():
    parser = argparse.ArgumentParser(description="Extract NVIDIA kernel patches from kernel-source.")
    parser.add_argument("base_rev", nargs="?", default="SL-16.1", help="Base revision or branch (default: SL-16.1)")
    parser.add_argument("target_rev", nargs="?", default=None, help="Target revision or branch (optional)")
    parser.add_argument("--base", dest="base_flag", help="Base revision/branch (alternative to positional argument)")
    parser.add_argument("--target", dest="target_flag", default="SL-16.1-NV", help="Target revision/branch (default: SL-16.1-NV)")
    parser.add_argument("--repo-dir", default=None, help="Path to local kernel-source checkout (if omitted, uses HTTPS)")
    parser.add_argument("--http", action="store_true", help="Force HTTPS fetch via kerncvs Gitweb")
    parser.add_argument("--remote-url", default="https://kerncvs.suse.de/git/?p=kernel-source.git", help="Base Gitweb URL")
    parser.add_argument("--format", choices=["asciidoc", "text", "json"], default="text", help="Output format")
    parser.add_argument("-o", "--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    base = args.base_flag if args.base_flag else args.base_rev
    target = args.target_flag if args.target_flag else (args.target_rev or "SL-16.1-NV")

    # Determine whether to use local git checkout or HTTPS
    repo = Path(args.repo_dir) if args.repo_dir else None
    use_http = args.http or repo is None or not (repo / "series.conf").exists()

    if use_http:
        patch_names = get_series_patches_http(args.remote_url, base, target)
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            records = list(executor.map(lambda name: fetch_patch_metadata_http(args.remote_url, target, name), patch_names))
    else:
        patch_names = get_series_patches(repo, base, args.target_rev)
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
