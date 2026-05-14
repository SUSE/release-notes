# SUSE Release Notes — Agent Quick Reference

## What this repo is

AsciiDoc source for SUSE product release notes, built with [doc-kit](https://github.com/openSUSE/doc-kit) via `daps`. No traditional test/lint/typecheck — `make validate` is the closest.

## File layout

```
DC-releasenotes_<product>        ← doc-kit config (points to MAIN= the master .adoc)
adoc/<product>/<version>/        ← version-specific .adoc files
adoc/<product>/                  ← master release-notes-*.adoc (includes version dirs)
adoc/common/                     ← shared includes (attributes, legal, about-rn, etc.)
adoc_postprocess.xsl             ← XSLT that cleans DocBook output from AsciiDoctor
```

Key entry points:
- **DC-*** files: one per product, controls build target and XSL params
- **adoc/\*/release-notes-*.adoc**: master include file; version content lives in subdirs
- **adoc/common/**: reusable includes shared across all products

## Editing notes

- **One sentence per line** — required by the style guide
- **Note IDs**: unique per document, format `[#jsc-SLE-1234]`, `[#bsc-00000]`, or `[#jsc-XXX-0000]`
- **Non-titled notes**: use `// jsc#SLE-1234` comment as fallback
- **Order within sections**: most important first; new notes go at the top of the section; additions before removals; minor changes and tables at bottom
- **One commit per note** — each change should be its own commit referencing the issue
- **Update revdate** — always update `:revdate:` in the master `.adoc` file (the `MAIN=` from the DC config file). Use today's date (`YYYY-MM-DD`)

### Commit messages

- **One-line subject** in imperative mood
- **Product/version prefix** — always include the product and version (e.g., `SLES 16.1:`, `SLE HA 16.1:`). For notes spanning multiple products, list all of them separated by commas (e.g., `SLES 16.0, SLES for SAP 16.0:`)
- **Issue reference** — always include `(jsc#XXXXX)` or `(bsc#XXXXX)` for single-issue commits; omit only if there is no associated issue
- **PR reference** — include `(#NN)` if the commit was squashed from a PR
- **Body** — typically unnecessary for single-note changes

Example:
```
SLES 16.1: Add note about Boot Loader Specification support (jsc#PED-10703)
```

## Building locally

```bash
# Validate (no output format)
make validate PRODUCT_VERSION=leap_16.0

# Preview HTML
make html PRODUCT_VERSION=leap_16.0

# Other formats: pdf, single-html, text, yast-html, all
make single-html PRODUCT_VERSION=leap_16.0

# Serve locally (needs Python 3.7+)
make serve
```

`PRODUCT_VERSION` must match the `DC-releasenotes_<PRODUCT_VERSION>` directory name.

## CI

`.github/workflows/asciidoc.yml` runs on push/PR when `DC-*` or `adoc/**` changes:
1. `openSUSE/doc-ci@gha-validate` — validates IDs, images, tables
2. `openSUSE/doc-ci@gha-build` — builds all DC-* targets
3. `SUSE/release-notes@gha-publish` — publishes to susedoc.github.io (main branch only)

## XSLT post-processing

`adoc_postprocess.xsl` fixes AsciiDoctor→DocBook output for GeekoDoc validation:
- `simpara` → `para`, `sidebar` → `note`, `literallayout` → `screen`
- Removes `authorinitials`, merges `othername`/`lineage` into `firstname`/`surname`
- Strips underscores from `xml:id` values
- Converts `formalpara[para/screen]` to `example`

## Shared notes

`adoc/shared.adoc` holds notes shared across versions using AsciiDoc tags:

```asciidoc
tag::TAGNAME[]
[#note-id]
= Title

Content...

end::TAGNAME[]
```

Include with: `include::../shared.adoc[tags=TAGNAME,leveloffset=+2]`

For product-specific shared notes (SLES 16.x), use `adoc/micro/shared.adoc` as reference for the tag pattern.

## Version structure

- **15 SP4–SP7**: monolithic — `release-notes.adoc` includes separate `.adoc` files (e.g., `security.adoc`, `network.adoc`) + has `changelog.adoc`
- **16.0–16.2**: monolithic — `release-notes-*.adoc` → `versionXXX.adoc` (all content inline, no separate section files)
- **Changelogs for 16.x**: stored in `release-notes-sles-<VERSION>-docinfo.xml` `<revhistory>` block, NOT in separate files
- **16.0/16.1**: include from `adoc/shared.adoc` using tags; 16.2 is a mostly-empty beta template

## Changelogs (docinfo.xml revhistory)

- **Never delete existing entries** — always add new ones to the top of the `<revhistory>`
- **Date** — use today's date (`YYYY-MM-DD`)
- **Multiple entries same day** — group under same `<revision>` with multiple `<listitem>` bullets
- **xlink namespace** — `<revhistory>` requires `xmlns:xlink="http://www.w3.org/1999/xlink"` when using `<link xlink:href="...">` (16.0 has it, 16.1+ need it added)

## Gotchas

- **Don't edit `Makefile` or `adoc/common/` directly** — both are upstream-managed and may be overwritten. Changes to `adoc/common/` should go through the doc-kit upstream.
- **`adoc_postprocess.xsl` is custom** — safe to edit locally; it's not upstream-managed.
- **IDs can't contain underscores** — the XSLT handles this, but prefer hyphens in note IDs.
- **PRs auto-assign to @KucharczykL** (`.github/workflows/CODEOWNERS`).
- **Lifecycle attribute**: set `:lifecycle: beta|maintained|unmaintained` in attributes-product.adoc to gate "prerelease" labels and doc URLs.

## Development environment

`.devcontainer/devcontainer.json` provides VSCode with the asciidoctor extension. Build deps (`daps`, `xsltproc`, doc-kit) are expected to be installed on the host.
