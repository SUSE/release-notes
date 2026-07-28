# PR Build Optimization Design Specification

## Overview
This document specifies the design for a durable, automatic dependency tracking solution to optimize GitHub Actions PR preview builds. The goal is to only validate and build the specific release note products (`DC-*` files) whose source AsciiDoc files or dependencies have been modified, vastly reducing PR build times.

## Architecture

The solution comprises two main components:
1. **Dynamic AsciiDoc Include-Tracer:** A Python script that recursively builds a true dependency graph of all `DC-*` files by parsing `include::` directives, mapping changed files to their parent products.
2. **GitHub Actions Workflow Refactoring:** A `detect` job that determines the git diff and runs the tracer, passing the dynamically filtered list of affected `DC-*` files to the `validate` and `build` jobs. The `build` job will employ `actions/cache` on the DAPS `build/` directory for true incremental compilation.

## 1. Dynamic Dependency Tracer (`scripts/detect-affected-dcs.py`)
* **Execution:** Reads a list of changed file paths from `stdin`.
* **Graph Building:** 
  * Identifies all `DC-*` files in the repository root.
  * For each `DC-*` file, reads its `MAIN` file path.
  * Recursively scans `.adoc` files starting from `MAIN`, searching for `include::[.../]<file_path>[\\[.*?\\]]`.
  * Resolves relative paths relative to the current file's directory.
  * Also flags sibling `.xml` files (e.g. `docinfo.xml`) and referenced image files as dependencies of the product.
* **Analysis & Safety Fallback:**
  * Iterates over the changed files from `stdin`.
  * If a changed file is determined to be "global" (i.e. not inside `adoc/` and not a `DC-*` file itself, such as `Makefile`, workflows, scripts), the script safely falls back to outputting **all** `DC-*` files to prevent silent breakage.
  * Otherwise, maps the changed file to all `DC-*` files that depend on it.
* **Output:** Prints a space-separated string of the affected `DC-*` files to `stdout` and exits.

## 2. GitHub Actions Workflow Integration (`.github/workflows/asciidoc.yml`)

### The `detect` Job
* **Purpose:** Run early to figure out the exact diff.
* **Logic:** 
  * Checks out code with `fetch-depth: 0` to access commit history.
  * Derives the base SHA and head SHA differently depending on whether it's a `pull_request` event or `push` event.
  * Runs `git diff --name-only $BASE_SHA $HEAD_SHA | uv run scripts/detect-affected-dcs.py`.
  * Passes the output into job outputs: `affected_dcs` and `has_changes` (boolean).

### The Cache Strategy
* **Location:** The DAPS compilation target `build/`.
* **Action:** Uses `actions/cache@v4` in the `build` job.
* **Keys:**
  * Cache Key: `${{ runner.os }}-daps-${{ github.ref_name }}-${{ github.sha }}`
  * Restore Keys: `${{ runner.os }}-daps-${{ github.ref_name }}-` -> `${{ runner.os }}-daps-`
* **Effect:** When compiling the limited set of affected DC files, DAPS will find the previously compiled XML/HTML assets in `build/` and only update what has actually changed.

### The `validate` and `build` Jobs
* Conditioned to run `if: needs.detect.outputs.has_changes == 'true'`.
* Both receive `dc-files: ${{ needs.detect.outputs.affected_dcs }}` instead of the hardcoded `"DC-*"`.

## Error Handling & Edge Cases
* **Empty Commits/No Affects:** If `has_changes` evaluates to false, validation and build are entirely skipped for the run.
* **Derived Products:** Because it relies on parsing the physical `include::../sles/...` tags, derived products like SLES for SAP and openSUSE Leap inherently rebuild if core SLES files are modified.
* **Shared Notes:** The `adoc/shared.adoc` file will correctly map to any DC file whose dependency chain includes it.