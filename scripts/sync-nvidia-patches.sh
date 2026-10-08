#!/usr/bin/env bash
set -euo pipefail

# sync-nvidia-patches.sh
# Fetches kernel-source, regenerates nvidia-patches-table.adoc, and opens/updates a GitHub PR if changed.

KERNEL_REPO_URL="${KERNEL_REPO_URL:-git://kerncvs.suse.de/kernel-source.git}"
KERNEL_DIR="${KERNEL_DIR:-.cache/kernel-source}"
BASE_BRANCH="${BASE_BRANCH:-origin/SL-16.1}"
TARGET_BRANCH="${TARGET_BRANCH:-SL-16.1-NV}"
OUTPUT_ADOC="${OUTPUT_ADOC:-adoc/sles/16.1/nvidia-patches-table.adoc}"
MASTER_DOC="${MASTER_DOC:-adoc/sles/release-notes-sles-161.adoc}"
GITHUB_REPO="${GITHUB_REPO:-SUSE/release-notes}"
GITHUB_TOKEN="${GITHUB_TOKEN:-${GIT_TOKEN:-}}"
DATE_TAG="$(date +%Y%m%d)"
SYNC_BRANCH="${SYNC_BRANCH:-sync/nvidia-kernel-patches-16.1}"

BASE_REF="${BASE_BRANCH##origin/}"
TARGET_REF="${TARGET_BRANCH##origin/}"

echo "==> Preparing kernel-source in ${KERNEL_DIR}..."
if [ ! -d "${KERNEL_DIR}/.git" ]; then
    mkdir -p "${KERNEL_DIR}"
    git -C "${KERNEL_DIR}" init
    git -C "${KERNEL_DIR}" remote add origin "${KERNEL_REPO_URL}"
fi

echo "==> Fetching branches with depth 1..."
git -C "${KERNEL_DIR}" fetch --depth 1 origin "${BASE_REF}:refs/remotes/origin/${BASE_REF}"
git -C "${KERNEL_DIR}" fetch --depth 1 origin "${TARGET_REF}:refs/remotes/origin/${TARGET_REF}"
git -C "${KERNEL_DIR}" checkout -f "origin/${TARGET_REF}"

echo "==> Extracting patches..."
python3 scripts/fetch-nvidia-kernel-patches.py \
    --repo-dir "${KERNEL_DIR}" \
    "origin/${BASE_REF}" \
    --format asciidoc \
    -o "${OUTPUT_ADOC}"

echo "==> Checking for documentation changes..."
if git diff --quiet "${OUTPUT_ADOC}"; then
    echo "No changes in NVIDIA kernel patch list. Exiting."
    exit 0
fi

echo "==> Changes detected in ${OUTPUT_ADOC}."
if [ -z "${GITHUB_TOKEN}" ]; then
    echo "Notice: GITHUB_TOKEN is not set. Updated ${OUTPUT_ADOC} locally without opening PR."
    exit 0
fi

TODAY="$(date +%Y-%m-%d)"
if [ -f "${MASTER_DOC}" ]; then
    sed -i -E "s/^:revdate: [0-9]{4}-[0-9]{2}-[0-9]{2}/:revdate: ${TODAY}/" "${MASTER_DOC}"
    git add "${MASTER_DOC}"
fi

git checkout -B "${SYNC_BRANCH}"
git add "${OUTPUT_ADOC}"
git commit -m "SLES 16.1: Update NVIDIA kernel patches list (${DATE_TAG}) (jsc#PED-16790)"

AUTH_HEADER="Authorization: Basic $(printf 'x-access-token:%s' "${GITHUB_TOKEN}" | base64 -w 0)"
git -c "http.extraHeader=${AUTH_HEADER}" push -u "https://github.com/${GITHUB_REPO}.git" "${SYNC_BRANCH}" --force

echo "==> Checking for existing Pull Request..."
PR_CHECK_URL="https://api.github.com/repos/${GITHUB_REPO}/pulls?head=${GITHUB_REPO%/*}:${SYNC_BRANCH}&state=open"
EXISTING_PR=$(curl -sS -H "Authorization: token ${GITHUB_TOKEN}" "${PR_CHECK_URL}" | grep -o '"number": [0-9]*' | head -n 1 | awk '{print $2}' || true)

if [ -n "${EXISTING_PR}" ]; then
    echo "==> Pull Request #${EXISTING_PR} already exists for ${SYNC_BRANCH}. Branch updated."
    exit 0
fi

echo "==> Opening GitHub Pull Request..."
curl -sS -f -X POST \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${GITHUB_REPO}/pulls" \
    -d "{
        \"title\": \"SLES 16.1: Update NVIDIA kernel patches list (${DATE_TAG}) (jsc#PED-16790)\",
        \"head\": \"${SYNC_BRANCH}\",
        \"base\": \"main\",
        \"body\": \"Automated bi-weekly update of NVIDIA kernel patches from ${TARGET_BRANCH}.\"
    }"
echo "==> Pull Request created successfully."

