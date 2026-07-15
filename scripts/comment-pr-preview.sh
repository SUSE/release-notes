#!/bin/bash
# scripts/comment-pr-preview.sh
# Comments on the pull request with active preview URLs

set -e

PR_NUMBER="${1}"
REPO="${2}"

if [ -z "$PR_NUMBER" ] || [ -z "$REPO" ]; then
  echo "Error: PR number and REPO are required. Usage: $0 <PR_NUMBER> <REPO>"
  exit 1
fi

# Find existing comment to avoid duplicate comments
comment_id=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json comments --jq '.comments[] | select(.body | contains("Release Notes Preview is ready!")) | .url' | grep -oP '\d+$' | head -n1)

body="🚀 **Release Notes Preview is ready!**

You can preview the built release notes here:
- [SLES 16.1](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/sles-16.1/html/release-notes/)
- [SLES 16.0](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/sles-16.0/html/release-notes/)
- [SLE HA 16.1](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/sleha-16.1/html/release-notes/)
- [SLE HA 16.0](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/sleha-16.0/html/release-notes/)
- [SLES for SAP 16.1](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/slesap-16.1/html/release-notes/)
- [SLES for SAP 16.0](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/slesap-16.0/html/release-notes/)
- [openSUSE Leap 16.1](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/leap-16.1/html/release-notes/)
- [openSUSE Leap 16.0](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/leap-16.0/html/release-notes/)
- [SLE Micro 6.2](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/sl-micro_62/html/release-notes/)
- [SLE Micro 6.1](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/sl-micro_61/html/release-notes/)
- [SLE Micro 6.0](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/sl-micro_60/html/release-notes/)

Directory Index: https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/"

if [ -n "$comment_id" ]; then
  gh api -X PATCH "repos/${REPO}/issues/comments/$comment_id" -f body="$body"
else
  gh pr comment "$PR_NUMBER" --repo "$REPO" --body "$body"
fi
