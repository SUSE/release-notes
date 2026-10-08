#!/usr/bin/env bash
set -euo pipefail

# test_sync_script.sh
# Test suite for scripts/sync-nvidia-patches.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNC_SCRIPT="${SCRIPT_DIR}/scripts/sync-nvidia-patches.sh"
FETCH_SCRIPT="${SCRIPT_DIR}/scripts/fetch-nvidia-kernel-patches.py"

echo "==> Setting up isolated test environment..."
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

MOCK_KERNEL="${TMP_DIR}/mock-kernel"
MOCK_REMOTE="${TMP_DIR}/mock-remote-rn.git"
MOCK_RN="${TMP_DIR}/mock-rn"
MOCK_BIN="${TMP_DIR}/bin"

mkdir -p "${MOCK_BIN}"

# Default mock gh that exits 1 to simulate absent/unauthenticated gh
cat << 'EOF' > "${MOCK_BIN}/gh"
#!/usr/bin/env bash
exit 1
EOF
chmod +x "${MOCK_BIN}/gh"

# 1. Setup mock kernel-source repository
mkdir -p "${MOCK_KERNEL}"
git -C "${MOCK_KERNEL}" init
git -C "${MOCK_KERNEL}" config user.name "Test User"
git -C "${MOCK_KERNEL}" config user.email "test@example.com"

# Create base branch SL-16.1
mkdir -p "${MOCK_KERNEL}/patches.suse"
echo "# series.conf" > "${MOCK_KERNEL}/series.conf"
git -C "${MOCK_KERNEL}" add series.conf
git -C "${MOCK_KERNEL}" commit -m "Initial commit on base"
git -C "${MOCK_KERNEL}" branch -m SL-16.1

# Create target branch SL-16.1-NV with an NVIDIA patch
git -C "${MOCK_KERNEL}" checkout -b SL-16.1-NV
echo "patches.suse/nvidia-test.patch # [NVIDIA]" >> "${MOCK_KERNEL}/series.conf"
cat << 'EOF' > "${MOCK_KERNEL}/patches.suse/nvidia-test.patch"
Git-commit: 1234567890abcdef1234567890abcdef12345678
Patch-mainline: v6.12-rc1
References: jsc#PED-16790
Subject: [PATCH] nvidia: add test patch

Fixes nvidia driver issue.
EOF
git -C "${MOCK_KERNEL}" add series.conf patches.suse/nvidia-test.patch
git -C "${MOCK_KERNEL}" commit -m "Add nvidia test patch"

# Convert mock kernel to bare repo to serve as remote
MOCK_KERNEL_GIT="${TMP_DIR}/mock-kernel.git"
git clone --bare "${MOCK_KERNEL}" "${MOCK_KERNEL_GIT}"

# 2. Setup mock bare release-notes remote for pushing PR branches
git init --bare "${MOCK_REMOTE}"

# 3. Setup mock release-notes workspace
mkdir -p "${MOCK_RN}/scripts" "${MOCK_RN}/adoc/sles/16.1"
cp "${SYNC_SCRIPT}" "${MOCK_RN}/scripts/sync-nvidia-patches.sh"
cp "${FETCH_SCRIPT}" "${MOCK_RN}/scripts/fetch-nvidia-kernel-patches.py"
chmod +x "${MOCK_RN}/scripts/sync-nvidia-patches.sh"
chmod +x "${MOCK_RN}/scripts/fetch-nvidia-kernel-patches.py"

git -C "${MOCK_RN}" init
git -C "${MOCK_RN}" config user.name "Test User"
git -C "${MOCK_RN}" config user.email "test@example.com"
git -C "${MOCK_RN}" remote add origin "${MOCK_REMOTE}"

touch "${MOCK_RN}/adoc/sles/16.1/nvidia-patches-table.adoc"
git -C "${MOCK_RN}" add .
git -C "${MOCK_RN}" commit -m "Initial release-notes commit"
git -C "${MOCK_RN}" branch -m main
git -C "${MOCK_RN}" push -u origin main

echo "==> Test 1: Dry-run flag --dry-run (changes detected, no branch or PR)..."
LOG1="${TMP_DIR}/test1.log"
(
    cd "${MOCK_RN}"
    PATH="${MOCK_BIN}:${PATH}" \
    KERNEL_REPO_URL="file://${MOCK_KERNEL_GIT}" \
    KERNEL_DIR="${TMP_DIR}/kernel-cache" \
    BASE_BRANCH="origin/SL-16.1" \
    TARGET_BRANCH="SL-16.1-NV" \
    OUTPUT_ADOC="adoc/sles/16.1/nvidia-patches-table.adoc" \
    ./scripts/sync-nvidia-patches.sh --dry-run > "${LOG1}" 2>&1
)

grep -q "Dry-run mode enabled: changes detected but no commit or pull request will be created." "${LOG1}" || {
    echo "FAILED: Test 1 expected dry-run log not found."
    cat "${LOG1}"
    exit 1
}
if git -C "${MOCK_RN}" branch --list "sync/nvidia-kernel-patches-16.1" | grep -q "sync/nvidia-kernel-patches-16.1"; then
    echo "FAILED: Test 1 branch was unexpectedly created in dry-run mode."
    exit 1
fi
echo "PASSED: Test 1 (--dry-run flag handled properly without creating branch)"

echo "==> Test 2: No changes exist in patch table..."
LOG2="${TMP_DIR}/test2.log"
git -C "${MOCK_RN}" add adoc/sles/16.1/nvidia-patches-table.adoc
git -C "${MOCK_RN}" commit -m "Commit patch table"

(
    cd "${MOCK_RN}"
    PATH="${MOCK_BIN}:${PATH}" \
    KERNEL_REPO_URL="file://${MOCK_KERNEL_GIT}" \
    KERNEL_DIR="${TMP_DIR}/kernel-cache" \
    BASE_BRANCH="origin/SL-16.1" \
    TARGET_BRANCH="SL-16.1-NV" \
    OUTPUT_ADOC="adoc/sles/16.1/nvidia-patches-table.adoc" \
    ./scripts/sync-nvidia-patches.sh > "${LOG2}" 2>&1
)

grep -q "No changes in NVIDIA kernel patch list. Exiting." "${LOG2}" || {
    echo "FAILED: Test 2 expected 'No changes' log not found."
    cat "${LOG2}"
    exit 1
}
echo "PASSED: Test 2 (No changes exist)"

echo "==> Test 3: Token provided, mock curl & push to local remote..."
LOG3="${TMP_DIR}/test3.log"
CURL_LOG="${TMP_DIR}/curl_calls.log"

cat << EOF > "${MOCK_BIN}/curl"
#!/usr/bin/env bash
echo "\$@" >> "${CURL_LOG}"
if [[ "\$*" == *"state=open"* ]]; then
    echo '[]'
else
    echo '{"number": 1, "html_url": "https://github.com/SUSE/release-notes/pull/1"}'
fi
EOF
chmod +x "${MOCK_BIN}/curl"

echo "// Stale table" > "${MOCK_RN}/adoc/sles/16.1/nvidia-patches-table.adoc"
git -C "${MOCK_RN}" add adoc/sles/16.1/nvidia-patches-table.adoc
git -C "${MOCK_RN}" commit -m "Reset table to stale state"

git -C "${MOCK_RN}" config url."file://${MOCK_REMOTE}".insteadOf "https://github.com/mock-org/mock-repo.git"

(
    cd "${MOCK_RN}"
    PATH="${MOCK_BIN}:${PATH}" \
    KERNEL_REPO_URL="file://${MOCK_KERNEL_GIT}" \
    KERNEL_DIR="${TMP_DIR}/kernel-cache" \
    BASE_BRANCH="origin/SL-16.1" \
    TARGET_BRANCH="SL-16.1-NV" \
    OUTPUT_ADOC="adoc/sles/16.1/nvidia-patches-table.adoc" \
    GITHUB_REPO="mock-org/mock-repo" \
    GITHUB_TOKEN="dummy-token" \
    ./scripts/sync-nvidia-patches.sh > "${LOG3}" 2>&1
)

grep -q "==> Pull Request created successfully." "${LOG3}" || {
    echo "FAILED: Test 3 expected PR creation log not found."
    cat "${LOG3}"
    exit 1
}

grep -q "https://api.github.com/repos/mock-org/mock-repo/pulls" "${CURL_LOG}" || {
    echo "FAILED: Test 3 mock curl was not called with expected API endpoint."
    cat "${CURL_LOG}"
    exit 1
}

echo "PASSED: Test 3 (Token provided, git push & curl mocked)"

echo "==> Test 4: Idempotency (open PR already exists via API)..."
LOG4="${TMP_DIR}/test4.log"
cat << 'EOF' > "${MOCK_BIN}/curl"
#!/usr/bin/env bash
if [[ "$*" == *"state=open"* ]]; then
    echo '[{"number": 42, "html_url": "https://github.com/mock-org/mock-repo/pull/42"}]'
else
    echo "ERROR: Should not call POST when PR already exists" >&2
    exit 1
fi
EOF

echo "// Stale table 2" > "${MOCK_RN}/adoc/sles/16.1/nvidia-patches-table.adoc"
git -C "${MOCK_RN}" add adoc/sles/16.1/nvidia-patches-table.adoc
git -C "${MOCK_RN}" commit -m "Reset table to stale state 2"

(
    cd "${MOCK_RN}"
    PATH="${MOCK_BIN}:${PATH}" \
    KERNEL_REPO_URL="file://${MOCK_KERNEL_GIT}" \
    KERNEL_DIR="${TMP_DIR}/kernel-cache" \
    BASE_BRANCH="origin/SL-16.1" \
    TARGET_BRANCH="SL-16.1-NV" \
    OUTPUT_ADOC="adoc/sles/16.1/nvidia-patches-table.adoc" \
    GITHUB_REPO="mock-org/mock-repo" \
    GITHUB_TOKEN="dummy-token" \
    ./scripts/sync-nvidia-patches.sh > "${LOG4}" 2>&1
)

grep -q "==> Pull Request #42 already exists for sync/nvidia-kernel-patches-16.1. Branch updated." "${LOG4}" || {
    echo "FAILED: Test 4 expected existing PR update log not found."
    cat "${LOG4}"
    exit 1
}
echo "PASSED: Test 4 (Idempotency - existing PR updated without error)"

echo "==> Test 5: gh CLI native mode..."
LOG5="${TMP_DIR}/test5.log"
GH_LOG="${TMP_DIR}/gh_calls.log"

cat << EOF > "${MOCK_BIN}/gh"
#!/usr/bin/env bash
echo "\$@" >> "${GH_LOG}"
if [ "\$1" = "auth" ] && [ "\$2" = "status" ]; then
    exit 0
elif [ "\$1" = "pr" ] && [ "\$2" = "list" ]; then
    exit 0
elif [ "\$1" = "pr" ] && [ "\$2" = "create" ]; then
    echo "https://github.com/mock-org/mock-repo/pull/101"
    exit 0
fi
EOF
chmod +x "${MOCK_BIN}/gh"

echo "// Stale table gh" > "${MOCK_RN}/adoc/sles/16.1/nvidia-patches-table.adoc"
git -C "${MOCK_RN}" add adoc/sles/16.1/nvidia-patches-table.adoc
git -C "${MOCK_RN}" commit -m "Reset table for gh test"

(
    cd "${MOCK_RN}"
    PATH="${MOCK_BIN}:${PATH}" \
    KERNEL_REPO_URL="file://${MOCK_KERNEL_GIT}" \
    KERNEL_DIR="${TMP_DIR}/kernel-cache" \
    BASE_BRANCH="origin/SL-16.1" \
    TARGET_BRANCH="SL-16.1-NV" \
    OUTPUT_ADOC="adoc/sles/16.1/nvidia-patches-table.adoc" \
    GITHUB_REPO="mock-org/mock-repo" \
    GITHUB_TOKEN="" \
    ./scripts/sync-nvidia-patches.sh > "${LOG5}" 2>&1
)

grep -q "==> Opening GitHub Pull Request via gh..." "${LOG5}" || {
    echo "FAILED: Test 5 expected gh pr create log not found."
    cat "${LOG5}"
    exit 1
}
grep -q "pr create" "${GH_LOG}" || {
    echo "FAILED: Test 5 gh pr create was not called."
    cat "${GH_LOG}"
    exit 1
}
echo "PASSED: Test 5 (gh CLI native mode)"

# Reset mock gh to exit 1 for remaining tests
cat << 'EOF' > "${MOCK_BIN}/gh"
#!/usr/bin/env bash
exit 1
EOF

echo "==> Test 6: Standalone runner mode (clones release-notes into .cache/release-notes)..."
LOG6="${TMP_DIR}/test6.log"
STANDALONE_DIR="${TMP_DIR}/standalone-runner"
mkdir -p "${STANDALONE_DIR}/scripts"
cp "${SYNC_SCRIPT}" "${STANDALONE_DIR}/scripts/sync-nvidia-patches.sh"
cp "${FETCH_SCRIPT}" "${STANDALONE_DIR}/scripts/fetch-nvidia-kernel-patches.py"
chmod +x "${STANDALONE_DIR}/scripts/"*

(
    cd "${STANDALONE_DIR}"
    PATH="${MOCK_BIN}:${PATH}" \
    KERNEL_REPO_URL="file://${MOCK_KERNEL_GIT}" \
    KERNEL_DIR="${TMP_DIR}/kernel-cache" \
    BASE_BRANCH="origin/SL-16.1" \
    TARGET_BRANCH="SL-16.1-NV" \
    RN_REPO_URL="file://${MOCK_REMOTE}" \
    GITHUB_REPO="mock-org/mock-repo" \
    GITHUB_TOKEN="" \
    ./scripts/sync-nvidia-patches.sh --dry-run > "${LOG6}" 2>&1
)

grep -q "==> Shallow cloning mock-org/mock-repo into .cache/release-notes..." "${LOG6}" || {
    echo "FAILED: Test 6 expected shallow clone log not found."
    cat "${LOG6}"
    exit 1
}
test -f "${STANDALONE_DIR}/.cache/release-notes/adoc/sles/16.1/nvidia-patches-table.adoc" || {
    echo "FAILED: Test 6 expected generated table in .cache/release-notes not found."
    exit 1
}
echo "PASSED: Test 6 (Standalone runner mode correctly clones and generates)"

echo "==> ALL TESTS PASSED SUCCESSFULLY!"
