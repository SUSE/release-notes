#!/bin/bash
# scripts/prepare-publish-hierarchy.sh
# Prepares the folder hierarchy for susedoc.github.io (both production and PR previews)

set -e

SUBFOLDER="${1:-}" # e.g. "preview" or empty
REDIRECT_URL="${2:-https://susedoc.github.io/release-notes/sles-16.0/html/release-notes/}"

# If SUBFOLDER is not empty, add a trailing slash for paths
if [ -n "$SUBFOLDER" ]; then
  DEST_PREFIX="publish/$SUBFOLDER"
else
  DEST_PREFIX="publish"
fi

mkdir -p "$DEST_PREFIX"/sl-micro{_60,_61,_62}/html/release-notes
mkdir -p "$DEST_PREFIX"/sles-16.0/html/release-notes
mkdir -p "$DEST_PREFIX"/sles-16.1/html/release-notes
mkdir -p "$DEST_PREFIX"/sleha-16.0/html/release-notes
mkdir -p "$DEST_PREFIX"/sleha-16.1/html/release-notes
mkdir -p "$DEST_PREFIX"/slesap-16.0/html/release-notes
mkdir -p "$DEST_PREFIX"/slesap-16.1/html/release-notes
mkdir -p "$DEST_PREFIX"/sles-16_SP0/html/release-notes
mkdir -p "$DEST_PREFIX"/leap-16.0/html/release-notes
mkdir -p "$DEST_PREFIX"/leap-16.1/html/release-notes

OUTPUT_DIR=$(find artifact-dir -mindepth 1 -maxdepth 1 -type d)

mv "$OUTPUT_DIR/html/releasenotes_leap_16.0"/* "$DEST_PREFIX"/leap-16.0/html/release-notes
mv "$OUTPUT_DIR/html/releasenotes_leap_16.1"/* "$DEST_PREFIX"/leap-16.1/html/release-notes
mv "$OUTPUT_DIR/html/releasenotes_sle-ha_16.0"/* "$DEST_PREFIX"/sleha-16.0/html/release-notes
mv "$OUTPUT_DIR/html/releasenotes_sle-ha_16.1"/* "$DEST_PREFIX"/sleha-16.1/html/release-notes
mv "$OUTPUT_DIR/html/releasenotes_sle-micro_6.0"/* "$DEST_PREFIX"/sl-micro_60/html/release-notes
mv "$OUTPUT_DIR/html/releasenotes_sle-micro_6.1"/* "$DEST_PREFIX"/sl-micro_61/html/release-notes
mv "$OUTPUT_DIR/html/releasenotes_sle-micro_6.2"/* "$DEST_PREFIX"/sl-micro_62/html/release-notes
mv "$OUTPUT_DIR/html/releasenotes_sles_16.0"/* "$DEST_PREFIX"/sles-16.0/html/release-notes
mv "$OUTPUT_DIR/html/releasenotes_sles_16.1"/* "$DEST_PREFIX"/sles-16.1/html/release-notes
mv "$OUTPUT_DIR/html/releasenotes_sles-sap_16.0"/* "$DEST_PREFIX"/slesap-16.0/html/release-notes
mv "$OUTPUT_DIR/html/releasenotes_sles-sap_16.1"/* "$DEST_PREFIX"/slesap-16.1/html/release-notes

echo "<meta http-equiv=\"refresh\" content=\"0;${REDIRECT_URL}\">" > "$DEST_PREFIX"/sles-16_SP0/html/release-notes/index.html

rm -rf artifact-dir
mv publish artifact-dir
