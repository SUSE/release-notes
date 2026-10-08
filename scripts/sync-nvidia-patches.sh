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
