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

pretty_name() {
  case $1 in
    sles-16.0) echo "SLES 16.0" ;;
    sles-16.1) echo "SLES 16.1" ;;
    sles-16.2) echo "SLES 16.2" ;;
    sles-16_SP0) echo "SLES 16 SP0 (Redirect)" ;;
    sleha-16.0) echo "SLE HA 16.0" ;;
    sleha-16.1) echo "SLE HA 16.1" ;;
    slesap-16.0) echo "SLES for SAP 16.0" ;;
    slesap-16.1) echo "SLES for SAP 16.1" ;;
    leap-16.0) echo "openSUSE Leap 16.0" ;;
    leap-16.1) echo "openSUSE Leap 16.1" ;;
    sl-micro_60) echo "SLE Micro 6.0" ;;
    sl-micro_61) echo "SLE Micro 6.1" ;;
    sl-micro_62) echo "SLE Micro 6.2" ;;
    sl-micro_63) echo "SLE Micro 6.3" ;;
    *)
      # Fallback: capitalize and replace hyphen/underscore
      echo "$1" | tr '_-' '  ' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1'
      ;;
  esac
}

# Find all DC-* files for active products and build links dynamically
links=""
for dc_file in DC-releasenotes_*; do
  [ -f "$dc_file" ] || continue
  
  # Extract the suffix after DC-releasenotes_
  suffix="${dc_file#DC-releasenotes_}"
  
  # Map the suffix to the published directory name
  case "$suffix" in
    sles_16.0) p="sles-16.0" ;;
    sles_16.1) p="sles-16.1" ;;
    sles_16.2) p="sles-16.2" ;;
    sle-ha_16.0) p="sleha-16.0" ;;
    sle-ha_16.1) p="sleha-16.1" ;;
    sles-sap_16.0) p="slesap-16.0" ;;
    sles-sap_16.1) p="slesap-16.1" ;;
    leap_16.0) p="leap-16.0" ;;
    leap_16.1) p="leap-16.1" ;;
    sle-micro_6.0) p="sl-micro_60" ;;
    sle-micro_6.1) p="sl-micro_61" ;;
    sle-micro_6.2) p="sl-micro_62" ;;
    sle-micro_6.3) p="sl-micro_63" ;;
    *) p="" ;; # Ignore legacy/unmapped DC files
  esac
  
  # Only link if the mapped directory actually exists in the built preview folder
  if [ -n "$p" ] && [ -d "artifact-dir/preview/$p" ]; then
    title=$(pretty_name "$p")
    links="${links}- [$title](https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/${p}/html/release-notes/)\n"
  fi
done

# Find existing comment to avoid duplicate comments
comment_id=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json comments --jq '.comments[] | select(.body | contains("Release Notes Preview is ready!")) | .url' | grep -oP '\d+$' | head -n1)

body="🚀 **Release Notes Preview is ready!**

You can preview the built release notes here:
$(echo -e "$links")
Directory Index: https://susedoc.github.io/release-notes/refs,pull,${PR_NUMBER},merge/"

if [ -n "$comment_id" ]; then
  gh api -X PATCH "repos/${REPO}/issues/comments/$comment_id" -f body="$body"
else
  gh pr comment "$PR_NUMBER" --repo "$REPO" --body "$body"
fi
