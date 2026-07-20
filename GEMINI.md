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
- **Avoid reader-specific words** — do not refer to specific roles or actors (such as "developers" or "users") as they add no technical value. Keep the text completely objective, high-signal, and focused purely on the technical change and the required action.
- **Note IDs**: unique per document, format `[#jsc-SLE-1234]`, `[#bsc-00000]`, or `[#jsc-XXX-0000]`. Only use `[#id]` tags (anchors) for titled sections. Do NOT use them on single lines or list items (like bullet points), as they do not generate a clickable anchor in the rendered output.
- **Non-titled notes**: use the comment `// jsc#SLE-1234` above the note as a fallback, and append the issue identifier `(jsc#SLE-1234)` or `(bsc#1234567)` in parentheses to the end of the text.
- **Multiple issue references**: since a section can only have a single `[#id]` tag, use one identifier for the section ID and append the additional identifiers inline in parentheses at the end of the text.
- **Order within sections**: most important first; new notes (including includes) go at the top of the section, right after the list of entries without titles; additions before removals; minor changes and tables at bottom
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

**Shared notes:** when the commit touches `adoc/shared.adoc`, the prefix must list **all** products and versions that include the note (e.g. `SLES 16.0, SLES 16.1:`), not a generic component name.

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

`adoc/shared.adoc` holds notes shared across versions using AsciiDoc tags.

**CRITICAL RULE — INLINE VS SHARED:** Only place notes in `adoc/shared.adoc` if they are shared across *independent codebases or different major version streams* (for example, a note that applies to SLES 15 SP6 AND SLES 16.0).

* **NEVER use `shared.adoc` for notes specific to a single core baseline (e.g., SLES 16.1 only)**, even if the change applies to multiple derived products (like openSUSE Leap 16.1 or SLES for SAP 16.1).
* **Why?** Derived products inherit the SLES core release notes (such as `adoc/sles/version161.adoc`) directly. Placing the note inline in the SLES spec file automatically shares it with all derived products without needing any `shared.adoc` tags.
* If a note is specific to a single core/version, always write it as an inline note directly within that core's spec file.

```asciidoc
tag::TAGNAME[]
[#note-id]
= Title

Content...

end::TAGNAME[]
```

Include with: `include::../shared.adoc[tags=TAGNAME,leveloffset=+2]`

**`leveloffset` values:** match the section depth. Shared notes use `= Title` (single `=`). If the include is under `== Section`, use `leveloffset=+2`. If under `==== Subsection`, use `leveloffset=+4`.

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

- **Shared note commits always include all affected products in the prefix** — even though `adoc/shared.adoc` is a single file, the commit message must reflect every product/version that consumes the note.
- **Don't edit `Makefile` or `adoc/common/` directly** — both are upstream-managed and may be overwritten. Changes to `adoc/common/` should go through the doc-kit upstream.
- **`adoc_postprocess.xsl` is custom** — safe to edit locally; it's not upstream-managed.
- **IDs can't contain underscores** — the XSLT handles this, but prefer hyphens in note IDs.
- **PRs auto-assign to @KucharczykL** (`.github/workflows/CODEOWNERS`).
- **Lifecycle attribute**: set `:lifecycle: beta|maintained|unmaintained` in attributes-product.adoc to gate "prerelease" labels and doc URLs.

## Development environment

`.devcontainer/devcontainer.json` provides VSCode with the asciidoctor extension. Build deps (`daps`, `xsltproc`, doc-kit) are expected to be installed on the host.

# AI Agent Knowledge: Static Portal Directory Constraints
DO NOT flatten the directory structure of compiled release notes inside CI build or publish scripts.
The static draft host `susedoc.github.io` relies on an XSLT script that strictly hardcodes links as `<family>-<version>/<format>/<doc-name>/`.
If the directory layout is altered (e.g. flattening `/html/release-notes/`), it will break all index navigation on the draft portal.
Use `.github/product-registry.yml` as the single source of truth for these paths.
