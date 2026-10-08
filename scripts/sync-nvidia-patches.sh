#!/usr/bin/env bash
set -euo pipefail

# sync-nvidia-patches.sh
# Fetches kernel-source, regenerates nvidia-patches-table.adoc, and opens/updates a GitHub PR if changed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

KERNEL_REPO_URL="${KERNEL_REPO_URL:-git://kerncvs.suse.de/kernel-source.git}"
KERNEL_DIR="${KERNEL_DIR:-}"
BASE_BRANCH="${BASE_BRANCH:-origin/SL-16.1}"
TARGET_BRANCH="${TARGET_BRANCH:-SL-16.1-NV}"
GITHUB_REPO="${GITHUB_REPO:-SUSE/release-notes}"
GITHUB_TOKEN="${GITHUB_TOKEN:-${GIT_TOKEN:-}}"
DATE_TAG="$(date +%Y%m%d)"
SYNC_BRANCH="${SYNC_BRANCH:-sync/nvidia-kernel-patches-16.1}"
DRY_RUN=false

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Synchronizes NVIDIA kernel patches for SLES 16.1 into SUSE Release Notes.
Extracts patch metadata via HTTPS from kerncvs (or a local kernel-source checkout),
detects documentation changes, and creates or updates a GitHub pull request.

Options:
  -n, --dry-run          Extract and check for changes without committing, pushing, or opening a PR
  -k, --kernel-dir DIR   Path to local kernel-source checkout (if omitted, fetches over HTTPS)
  -b, --base REF         Base branch or revision (default: ${BASE_BRANCH})
  -t, --target REF       Target branch or revision (default: ${TARGET_BRANCH})
  -h, --help             Show this help message and exit

Environment Variables:
  GITHUB_TOKEN           GitHub personal access token (used in headless CI environments)
  KERNEL_DIR             Path to local kernel-source checkout
  DRY_RUN                Set to 1 or true to enable dry-run mode

Authentication:
  Prefers 'gh' CLI if installed and authenticated ('gh auth status').
  Falls back to GITHUB_TOKEN via HTTPS in CI/headless environments.
EOF
}

# Parse command line arguments
while [ $# -gt 0 ]; do
    case "$1" in
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -k|--kernel-dir)
            KERNEL_DIR="$2"
            shift 2
            ;;
        -b|--base)
            BASE_BRANCH="$2"
            shift 2
            ;;
        -t|--target)
            TARGET_BRANCH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [ "${DRY_RUN}" = "1" ] || [ "${DRY_RUN}" = "true" ]; then
    DRY_RUN=true
fi

# Determine release-notes workspace:
# If in release-notes repo (has adoc/), use current dir. Otherwise clone/fetch into .cache/release-notes
RN_REPO_URL="${RN_REPO_URL:-https://github.com/${GITHUB_REPO}.git}"
RN_DIR="${RN_DIR:-}"
if [ -z "${RN_DIR}" ]; then
    if [ -d "adoc" ]; then
        RN_DIR="."
    else
        RN_DIR=".cache/release-notes"
    fi
fi

OUTPUT_ADOC_REL="adoc/sles/16.1/nvidia-patches-table.adoc"
MASTER_DOC_REL="adoc/sles/release-notes-sles-161.adoc"

if [ "${RN_DIR}" = "." ]; then
    OUTPUT_ADOC="${OUTPUT_ADOC:-${OUTPUT_ADOC_REL}}"
    MASTER_DOC="${MASTER_DOC:-${MASTER_DOC_REL}}"
else
    OUTPUT_ADOC="${OUTPUT_ADOC:-${RN_DIR}/${OUTPUT_ADOC_REL}}"
    MASTER_DOC="${MASTER_DOC:-${RN_DIR}/${MASTER_DOC_REL}}"
fi

if [ "${RN_DIR}" != "." ]; then
    if [ ! -d "${RN_DIR}/.git" ]; then
        echo "==> Shallow cloning ${GITHUB_REPO} into ${RN_DIR}..."
        git clone --depth 1 "${RN_REPO_URL}" "${RN_DIR}"
    else
        echo "==> Updating ${RN_DIR} from ${RN_REPO_URL}..."
        git -C "${RN_DIR}" fetch --depth 1 origin main
        git -C "${RN_DIR}" checkout -f origin/main
    fi
fi

BASE_REF="${BASE_BRANCH##origin/}"
TARGET_REF="${TARGET_BRANCH##origin/}"

echo "==> Extracting patches..."
mkdir -p "$(dirname "${OUTPUT_ADOC}")"

if [ -n "${KERNEL_DIR}" ] && [ -d "${KERNEL_DIR}/.git" ]; then
    echo "==> Using local kernel-source checkout at ${KERNEL_DIR}..."
    python3 "${SCRIPT_DIR}/fetch-nvidia-kernel-patches.py" \
        --repo-dir "${KERNEL_DIR}" \
        "origin/${BASE_REF}" \
        --format asciidoc \
        -o "${OUTPUT_ADOC}"
else
    echo "==> Fetching patches directly from kerncvs over HTTPS..."
    python3 "${SCRIPT_DIR}/fetch-nvidia-kernel-patches.py" \
        --http \
        --base "${BASE_REF}" \
        --target "${TARGET_REF}" \
        --format asciidoc \
        -o "${OUTPUT_ADOC}"
fi

echo "==> Checking for documentation changes..."
HAS_CHANGES=false
if ! git -C "${RN_DIR}" diff --quiet -- "${OUTPUT_ADOC_REL}"; then
    HAS_CHANGES=true
fi
if [ -n "$(git -C "${RN_DIR}" status --porcelain -- "${OUTPUT_ADOC_REL}")" ]; then
    HAS_CHANGES=true
fi

if [ "${HAS_CHANGES}" = false ]; then
    echo "No changes in NVIDIA kernel patch list. Exiting."
    exit 0
fi

echo "==> Changes detected in ${OUTPUT_ADOC}."

if [ "${DRY_RUN}" = true ]; then
    echo "==> Dry-run mode enabled: changes detected but no commit or pull request will be created."
    git -C "${RN_DIR}" diff --stat -- "${OUTPUT_ADOC_REL}"
    exit 0
fi

# Detect authentication mechanism
USE_GH=false
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    USE_GH=true
fi

if [ "${USE_GH}" = false ] && [ -z "${GITHUB_TOKEN}" ]; then
    echo "Notice: Neither authenticated gh CLI nor GITHUB_TOKEN is available. Updated ${OUTPUT_ADOC} locally without opening PR."
    exit 0
fi

TODAY="$(date +%Y-%m-%d)"
if [ -f "${MASTER_DOC}" ]; then
    sed -i -E "s/^:revdate: [0-9]{4}-[0-9]{2}-[0-9]{2}/:revdate: ${TODAY}/" "${MASTER_DOC}"
    git -C "${RN_DIR}" add "${MASTER_DOC_REL}"
fi

git -C "${RN_DIR}" checkout -B "${SYNC_BRANCH}"
git -C "${RN_DIR}" add "${OUTPUT_ADOC_REL}"
git -C "${RN_DIR}" commit -m "SLES 16.1: Update NVIDIA kernel patches list (${DATE_TAG}) (jsc#PED-16790)"

if [ "${USE_GH}" = true ]; then
    echo "==> Pushing branch ${SYNC_BRANCH} via git/gh..."
    git -C "${RN_DIR}" push -u origin "${SYNC_BRANCH}" --force

    echo "==> Checking for existing Pull Request via gh..."
    EXISTING_PR="$(gh pr list --repo "${GITHUB_REPO}" --head "${SYNC_BRANCH}" --state open --json number -q '.[0].number' 2>/dev/null || true)"

    if [ -n "${EXISTING_PR}" ]; then
        echo "==> Pull Request #${EXISTING_PR} already exists for ${SYNC_BRANCH}. Branch updated."
        exit 0
    fi

    echo "==> Opening GitHub Pull Request via gh..."
    gh pr create \
        --repo "${GITHUB_REPO}" \
        --base main \
        --head "${SYNC_BRANCH}" \
        --title "SLES 16.1: Update NVIDIA kernel patches list (${DATE_TAG}) (jsc#PED-16790)" \
        --body "Automated bi-weekly update of NVIDIA kernel patches from ${TARGET_BRANCH}."
    echo "==> Pull Request created successfully."
else
    echo "==> Pushing branch ${SYNC_BRANCH} via token..."
    AUTH_HEADER="Authorization: Basic $(printf 'x-access-token:%s' "${GITHUB_TOKEN}" | base64 -w 0)"
    git -C "${RN_DIR}" -c "http.extraHeader=${AUTH_HEADER}" push -u "https://github.com/${GITHUB_REPO}.git" "${SYNC_BRANCH}" --force

    echo "==> Checking for existing Pull Request via API..."
    PR_CHECK_URL="https://api.github.com/repos/${GITHUB_REPO}/pulls?head=${GITHUB_REPO%/*}:${SYNC_BRANCH}&state=open"
    EXISTING_PR=$(curl -sS -H "Authorization: token ${GITHUB_TOKEN}" "${PR_CHECK_URL}" | grep -o '"number": [0-9]*' | head -n 1 | awk '{print $2}' || true)

    if [ -n "${EXISTING_PR}" ]; then
        echo "==> Pull Request #${EXISTING_PR} already exists for ${SYNC_BRANCH}. Branch updated."
        exit 0
    fi

    echo "==> Opening GitHub Pull Request via API..."
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
fi
