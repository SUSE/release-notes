# Automated Workflow for Publishing NVIDIA Kernel Patches

## Overview

This document specifies an automated workflow to extract, process, and publish the list of NVIDIA kernel patches for SUSE Linux Enterprise Server (SLES) 16.1 and future releases.

The list of patches changes approximately every two weeks during initial development phases and less frequently later in the product lifecycle. Because the patch list contains more than 200 items, it is maintained as a separate, linked document or file to preserve the readability of the main release notes.

---

## 1. Problem Statement and Constraints

1. **Source Repository Size & Access**:
   * **Source**: `git://kerncvs.suse.de/kernel-source.git` (branch `SL-16.1-NV` compared against `origin/SL-16.1`).
   * **Size**: ~4.5 GB.
   * **Network Boundary**: Hosted inside the SUSE internal engineering network behind the SUSE VPN. Public GitHub Actions runners cannot access it directly.
2. **Data Extraction**:
   * The patches to document are added to `series.conf` on the NVIDIA branch (`SL-16.1-NV`) relative to the base release (`origin/SL-16.1`).
   * Each patch file in `patches.suse/` contains metadata headers:
     * `Git-commit`: Upstream Linux kernel commit hash.
     * `Patch-mainline`: Upstream mainline kernel version tag (e.g., `v6.13-rc1`).
     * `References`: Tracking IDs (e.g., `jsc#NVIDIA-55`, `bsc#1272627`).
     * `Subject`: One-line patch summary.
   * Extraction logic exists in Ruby (`scripts/printpatchset` on branch `scripts`) and Python (`scripts/fetch-nvidia-kernel-patches.py`).
3. **Publishing Target**:
   * SUSE Documentation Server (`docserv`), which builds and serves content on `documentation.suse.com` (d.s.c).
   * Docserv clones `https://github.com/SUSE/release-notes.git` (`main` branch) and compiles deliverables using DAPS.
   * Apache rewrite rules in `docserv-config/server-root-files-doc-suse-com/.htaccess` control URLs under `https://documentation.suse.com/releasenotes/<product>/<version>/`.

---

## 2. Proposed Approaches

### Approach 1 (Recommended): GitLab CI Scheduled Pipeline + AsciiDoc Deliverable

* **Extraction Runner**:
  * Run a scheduled pipeline on internal SUSE GitLab (`gitlab.suse.de`) every two weeks.
  * Internal runners have direct network access to `kerncvs.suse.de`.
  * The job caches the repository or uses `git fetch --depth 1` / blobless clones (`--filter=blob:none`) to eliminate repeated 4.5 GB downloads.
  * An automated Python script executes `scripts/fetch-nvidia-kernel-patches.py`, parses the patch metadata, and outputs a formatted AsciiDoc file: `adoc/sles/16.1/nvidia-patches.adoc`.
  * The pipeline commits the file to a branch and creates a Pull Request on `SUSE/release-notes` via a GitHub token / bot.
* **Publishing**:
  * Configured as a deliverable in `docserv-config/config.d/releasenotes.xml` (e.g., `DC-releasenotes_sles-nvidia_16.1`) or as an included appendix.
  * Linked from `adoc/sles/version161.adoc` under the relevant architecture/hardware section.
  * Docserv builds the deliverable automatically on its regular Thursday schedule or on request.
* **Advantages**:
  * Fully automated end-to-end.
  * Follows standard SUSE documentation styling, search indexing, and DAPS toolchain.
  * Eliminates manual web server uploads and custom `.htaccess` exceptions.

---

### Approach 2: GitLab CI Scheduled Pipeline + Static File in Existing Docserv Rewrite

* **Extraction Runner**:
  * Same automated GitLab CI schedule on `gitlab.suse.de` as Approach 1.
  * The script generates a raw plain text file: `static/nvidia-patches.txt` (or inside the deliverable static path).
  * Automatically opens a PR to `SUSE/release-notes`.
* **Publishing**:
  * Uses the existing Apache rewrite rule in docserv's `.htaccess`:
    ```apache
    RewriteCond "%{DOCUMENT_ROOT}/en-us/releasenotes/$1/html/releasenotes_$1_$2/$3" -f
    RewriteRule "^releasenotes/([^/]+)/([^/]+)/(index\.html|static(/(.*)?))?" "/en-us/releasenotes/$1/html/releasenotes_$1_$2/$3" [PT,L]
    ```
  * Files under `static/` are served directly without modifying `.htaccess`.
  * Linked from `adoc/sles/version161.adoc` as a download link.
* **Advantages**:
  * Retains the requested plain `.txt` file format.
  * Does not require custom `.htaccess` modifications.
* **Disadvantages**:
  * Lacks doc navigation, styling, and metadata search indexing.
  * Requires verifying that DAPS copies the `static/` directory to docroot during compilation.

---

### Approach 3: Semi-Automated Local CLI Script + PR

* **Extraction Runner**:
  * A local shell script executed on the local workstation when connected to SUSE VPN.
  * Run bi-weekly on-demand or triggered by a local cron/calendar reminder.
  * Uses the existing local clone at `~/work/git/kernel-source`.
  * Executes the extraction script, updates `adoc/sles/16.1/nvidia-patches.adoc` (or `.txt`), creates a Git branch, and opens a GitHub PR with `gh pr create`.
* **Publishing**:
  * Merged into `SUSE/release-notes` `main` branch and built by docserv.
* **Advantages**:
  * Zero infrastructure setup required (no GitLab runner, no CI secret tokens).
  * Immediately operational.
* **Disadvantages**:
  * Requires manual intervention every two weeks.
  * Fails to update if the maintainer environment is unavailable.

---

## 3. Detailed Data Flow (Recommended Approach 1)

```mermaid
flowchart TD
    subgraph Internal Network [SUSE Internal Network / VPN]
        KS["kerncvs.suse.de/kernel-source.git\n(Branch: SL-16.1-NV)"]
        GL_CI["gitlab.suse.de Scheduled CI Job\n(Every 2 weeks)"]
        SCRIPT["fetch-nvidia-kernel-patches.py\n(Diff series.conf & parse patch headers)"]
        KS -->|git fetch incremental| GL_CI
        GL_CI -->|Run extraction| SCRIPT
    end

    subgraph GitHub [GitHub / Public]
        SCRIPT -->|gh pr create / API| PR["PR on SUSE/release-notes\n(adoc/sles/16.1/nvidia-patches.adoc)"]
        PR -->|Review & Merge| MAIN["SUSE/release-notes: main"]
    end

    subgraph Docserv [SUSE Documentation Server]
        MAIN -->|Weekly Pull / Trigger| DS["Docserv Build Engine (DAPS)"]
        DS -->|Compile HTML| DSC["documentation.suse.com\n(/releasenotes/sles/16.1/...)"]
    end
```

---

## 4. Implementation Plan

### Phase 1: Patch Extraction Script Enhancement
1. Update `scripts/fetch-nvidia-kernel-patches.py` to:
   * Extract `Git-commit`, `Patch-mainline`, `References` (`jsc#...`, `bsc#...`), and `Subject`.
   * Support an `--asciidoc` flag to format output directly as an AsciiDoc table.
   * Support a `--text` flag for plain-text tabular output.
2. Verify output locally against `~/work/git/kernel-source`.

### Phase 2: Documentation Integration
1. Add `adoc/sles/16.1/nvidia-patches.adoc` with proper document headers and metadata.
2. In `adoc/sles/version161.adoc`, add a note and hyperlink pointing to the patch reference page.
3. Configure `docserv-config/config.d/releasenotes.xml` (or verify inclusion in the main deliverable).

### Phase 3: Automation Setup
1. Create a lightweight pipeline repository on `gitlab.suse.de` with scheduled execution (every 14 days).
2. Configure a GitHub personal access token / deploy key to allow automated branch push and PR creation on `SUSE/release-notes`.
3. Test a dry-run execution of the automated pipeline.

---

## 5. Operational Instructions

This section describes the procedure to configure and operate the automated workflow on `gitlab.suse.de`.

### 5.1 Project Setup on GitLab

1. Log in to `gitlab.suse.de`.
2. Select **New Project** -> **Create blank project**.
3. Set the project name to `nvidia-patches-sync`.
4. Set the visibility level to **Internal**.
5. Push the repository containing `.gitlab-ci.yml` and `scripts/sync-nvidia-patches.sh` to this project.

### 5.2 Secret Variable Configuration

The automated script requires a GitHub token to create pull requests on `SUSE/release-notes`.

1. Generate a GitHub Personal Access Token (PAT) with `repo` scope permissions (repository write access).
2. Open the project on `gitlab.suse.de`.
3. Navigate to **Settings** -> **CI/CD** -> **Variables**.
4. Select **Add variable**.
5. Configure the variable:
   * **Key**: `GITHUB_TOKEN`
   * **Value**: `<github-personal-access-token>`
   * **Type**: `Variable`
   * **Flags**: Check **Mask variable** and **Protect variable**.
6. Select **Add variable**.

### 5.3 Pipeline Schedule Setup

Set up a recurring pipeline schedule to run every 14 days.

1. Navigate to **Build** -> **Pipeline schedules** in the GitLab project.
2. Select **New schedule**.
3. Enter `Bi-weekly NVIDIA Kernel Patch Sync` in **Description**.
4. Set **Interval Pattern** to **Custom** and enter a 14-day cron schedule:
   `0 2 */14 * *` (or select bi-weekly execution).
5. Set **Target branch** to `main`.
6. Select the **Activated** checkbox.
7. Select **Save pipeline schedule**.

### 5.4 Docserv Build Verification

Verify that docserv successfully compiles and publishes the generated patch table.

1. Verify that the GitLab CI job executes `scripts/sync-nvidia-patches.sh` and opens a GitHub Pull Request when changes occur.
2. Merge the Pull Request into the `main` branch of `SUSE/release-notes`.
3. Verify local build validation using DAPS:
   ```bash
   make validate PRODUCT_VERSION=sles_16.1
   ```
4. Verify docserv compilation on `documentation.suse.com` after the scheduled docserv sync:
   * Confirm `adoc/sles/16.1/nvidia-patches-table.adoc` renders correctly inside `adoc/sles/16.1/nvidia-patches.adoc`.
   * Check that all patch commit links, mainline versions, and tracker references display cleanly.

