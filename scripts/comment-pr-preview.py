#!/usr/bin/env python3
import os
import sys
import json
import re
import yaml
import subprocess

def run_command(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Warning: Command {' '.join(cmd)} failed with exit code {res.returncode}.", file=sys.stderr)
        if res.stderr:
            print(res.stderr, file=sys.stderr)
    return res.stdout, res.returncode

def main():
    if len(sys.argv) < 3:
        print("Usage: comment-pr-preview.py <PR_NUMBER> <REPO>", file=sys.stderr)
        sys.exit(1)

    pr_number = sys.argv[1]
    repo = sys.argv[2]

    # 1. Read product-registry.yml
    registry_path = ".github/product-registry.yml"
    if not os.path.exists(registry_path):
        print(f"Error: {registry_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(registry_path, "r") as f:
        registry = yaml.safe_load(f)

    # 2. Dynamically build the list of links based on built preview directories
    links = []
    for dc_file, meta in registry.items():
        slug = meta["slug"]
        version = meta["version"]
        short_name = meta["short-name"]
        doc_name = meta["doc-name"]

        # CRITICAL FIX: Since the preview directory is renamed to 'artifact-dir',
        # the product slugs reside directly under 'artifact-dir' (e.g. 'artifact-dir/sles-16.0').
        preview_path = os.path.join("artifact-dir", slug)

        if os.path.exists(preview_path):
            url = f"https://susedoc.github.io/release-notes/pr-{pr_number}/{slug}/html/{doc_name}/"
            links.append(f"- [{short_name} {version}]({url})")

    if not links:
        print("No previews built. Skipping comment.")
        sys.exit(0)

    links_block = "\n".join(links)
    body = f"🚀 **Release Notes Preview is ready!**\n\nYou can preview the built release notes here:\n{links_block}\n\nDirectory Index: https://susedoc.github.io/release-notes/pr-{pr_number}/"

    # 3. Query existing comments on the PR to avoid duplicate comment spam
    comment_stdout, _ = run_command([
        "gh", "pr", "view", pr_number, "--repo", repo, "--json", "comments"
    ])
    
    comment_id = None
    if comment_stdout:
        try:
            comments_data = json.loads(comment_stdout)
            for comment in comments_data.get("comments", []):
                if "Release Notes Preview is ready!" in comment.get("body", ""):
                    # ROBUST FIX: Extract the database ID securely using regular expressions
                    # matching the trailing digits at the end of the comment URL.
                    url = comment.get("url", "")
                    match = re.search(r"\d+$", url)
                    comment_id = match.group(0) if match else None
                    break
        except Exception as e:
            print(f"Warning: Failed to parse comments JSON: {e}", file=sys.stderr)

    # 4. Patch or Create the comment
    if comment_id:
        # Edit existing comment
        print(f"Updating existing comment {comment_id}...")
        run_command([
            "gh", "api", "-X", "PATCH", f"repos/{repo}/issues/comments/{comment_id}", "-f", f"body={body}"
        ])
    else:
        # Create new comment
        print("Creating new preview comment...")
        run_command([
            "gh", "pr", "comment", pr_number, "--repo", repo, "--body", body
        ])

if __name__ == "__main__":
    main()
