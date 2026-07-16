# Release Notes Publishing Architecture

## Overview
This repository compiles release notes for multiple products (SLES, SLE HA, SLES-SAP, SLE Micro, openSUSE Leap) on a single branch.

## The Dual-Portal Publishing Constraints

To prevent future regressions, developers must understand that our two primary publishing targets require completely different directory layouts:

### 1. Production Portal (documentation.suse.com via docserv)
- **Path on disk:** `/en-us/releasenotes/<acronym>/html/releasenotes_<acronym>_<version>/`
- **Link Mapping:** Managed inside `docserv-config`'s `config.d/releasenotes.xml` by specifying the `<dc>` file name.
- **URL virtualization:** Apache `.htaccess` PT (passthrough) RewriteRules map the raw DAPS output directory cleanly to `/releasenotes/<acronym>/<version>/`.

### 2. Draft/Nightly Portal (susedoc.github.io via GitHub Pages)
- **Path on disk:** `<slug>/html/<doc-name>/` (e.g., `sles-16.0/html/release-notes/`)
- **Link Mapping:** Hardcoded inside `susedoc.github.io`'s `config.xml` and parsed by an XSLT generator (`update-index.xsl`).
- **XSLT Rule:** Generates `href="{$url}/{$format}/{$doc}/"` (translating sles-16.0 to `sles-16.0/html/release-notes/`).
- **Constraint:** Since GitHub Pages lacks `.htaccess` RewriteRules, our CI scripts MUST manually construct this nested directory layout on the target pages repository, otherwise links on susedoc.github.io/index.html will 404.

## Single Source of Truth
The `.github/product-registry.yml` file maps each active DAPS build file (`DC-*`) to its taxonomic attributes (`slug`, `version`, `doc-name`), allowing both build and PR indexing tools to dynamically resolve these paths.
