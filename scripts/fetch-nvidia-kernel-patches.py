#!/usr/bin/env python3
"""
fetch-nvidia-kernel-patches.py

Python port of the kernel-source printpatchset script. Prints patches with
their subjects. Run it from the root of a kernel-source checkout.

Usage:
    fetch-nvidia-kernel-patches.py [-f] [REV]
    fetch-nvidia-kernel-patches.py [-f] REFERENCE
    fetch-nvidia-kernel-patches.py [-f] PATCH...

REV (default: @{U}) prints the patches added to series.conf since REV.
REFERENCE is any argument containing '#' (e.g. bsc#1234567); patches in
patches.suse/ mentioning it are printed in series.conf order.
Any other arguments are printed as patch paths.

-f also prints, recursively, the patches whose "Fixes:" tag references
each printed patch's Git-commit, indented and labeled "Fixed-by:".

Example (NVIDIA kernel patch set, on branch SL-16.1-NV):
    fetch-nvidia-kernel-patches.py origin/SL-16.1
"""

import re
import subprocess
import sys


def git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, errors="replace", check=False
    )


def read_series():
    with open("series.conf", encoding="utf-8", errors="replace") as f:
        return [line.strip() for line in f]


def header_value(patch, tag):
    """Words after the first on all lines containing tag (case-insensitive)."""
    try:
        with open(patch, encoding="utf-8", errors="replace") as f:
            lines = [line for line in f if tag.lower() in line.lower()]
    except OSError:
        return ""
    return " ".join("".join(lines).split()[1:])


def print_patch(patch, fixes, all_patches, seen, level=0):
    commit = header_value(patch, "Git-commit: ")
    subj = header_value(patch, "Subject: ")
    subj = re.sub(r"\[PATCH[^\]]*\] *", "", subj, count=1)
    if commit and commit in seen:
        return
    prefix = "   " * level + "Fixed-by: " if level else ""
    print(f'{prefix}{patch} ("{subj}")')
    if commit and fixes:
        seen.add(commit)
        fixed_by = set(git("grep", "-l", f"Fixes: {commit[:12]}").stdout.splitlines())
        for fix in all_patches:
            if fix in fixed_by:
                print_patch(fix, fixes, all_patches, seen, level + 1)


def main():
    args = sys.argv[1:]
    fixes = bool(args) and args[0] == "-f"
    if fixes:
        args = args[1:]
    if not args:
        args = ["@{U}"]

    if git("rev-parse", "--verify", "--quiet", args[0]).returncode == 0:
        diff = git("diff", args[0], "series.conf").stdout
        all_patches = patches = [
            line[1:].strip()
            for line in diff.splitlines(keepends=True)
            if re.match(r"\+[^+]", line) and "#" not in line and len(line) > 5
        ]
    elif "#" in args[0]:
        all_patches = read_series()
        matching = set(git("grep", "-l", args[0], "patches.suse").stdout.splitlines())
        patches = [p for p in all_patches if p in matching]
    else:
        all_patches = read_series() if fixes else []
        patches = args

    seen = set()
    for patch in patches:
        print_patch(patch, fixes, all_patches, seen)


if __name__ == "__main__":
    main()
