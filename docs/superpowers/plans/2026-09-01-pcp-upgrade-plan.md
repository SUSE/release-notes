# Performance Co-Pilot (PCP) Upgrade to 6.3.8 Release Note Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a release note documenting the upgrade of Performance Co-Pilot (PCP) from 6.2.0 to 6.3.8 in SLES 16.1, including updating master attributes and the SLES 16.1 docinfo changelog.

**Architecture:** Monolithic release note insertion into `adoc/sles/version161.adoc` under the `== Changes affecting all architectures` section. Includes updating docinfo XML with a `<revision>` entry and setting the `:revdate:` attribute on the version 16.1 master release notes file.

**Tech Stack:** AsciiDoc, XML (DocBook), DAPS validation engine.

## Global Constraints
- One sentence per line in AsciiDoc.
- SLES 16.1 content is monolithic, located under `adoc/sles/version161.adoc`.
- Update `adoc/sles/release-notes-sles-161-docinfo.xml` revision history `<revhistory>` with a new entry on top.
- Update `revdate` attribute in `adoc/sles/release-notes-sles-161.adoc` to `2026-09-01`.

---

### Task 1: Add inline release note in version161.adoc

**Files:**
- Modify: `adoc/sles/version161.adoc`

**Interfaces:**
- Consumes: None (starting task)
- Produces: The inline release note section under ID `[#jsc-PED-16216]`

- [ ] **Step 1: Locate insertion point**
Identify where to insert the new release note. We will insert it under the `== Changes affecting all architectures` section of `adoc/sles/version161.adoc`, right below the `curl` or `patch` updates.

- [ ] **Step 2: Add the release note**
In `adoc/sles/version161.adoc`, insert the following text:

```asciidoc
// jsc#PED-16216
[#jsc-PED-16216]
=== Performance Co-Pilot (PCP) upgraded to version 6.3.8

Performance Co-Pilot (PCP) has been upgraded from version 6.2.0 to 6.3.8.
This version upgrade introduces AMD GPU metric monitoring support in `pcp-htop`.
It adds Valkey support alongside Redis in `libpcp_web`.
This version upgrade also resolves multiple security vulnerabilities, including CVE-2024-45769 (bsc#1230551).
For a complete list of changes, see the upstream release notes at link:https://pcp.io/[] and the package changelog.
```

- [ ] **Step 3: Validate syntax**
Explain the command and run:
`make validate PRODUCT_VERSION=sles_16.1`
Expected: SUCCESS or validation warnings/errors if any other issues exist, but the newly added section should be parsed successfully.

---

### Task 2: Update Docinfo Revision History & Master Revdate

**Files:**
- Modify: `adoc/sles/release-notes-sles-161-docinfo.xml`
- Modify: `adoc/sles/release-notes-sles-161.adoc`

**Interfaces:**
- Consumes: The newly added section ID `jsc-PED-16216`
- Produces: Updated revdate and docinfo revision history entry referencing `jsc-PED-16216`

- [ ] **Step 1: Add new revision block in docinfo**
Add a revision block to the top of `<revhistory>` in `adoc/sles/release-notes-sles-161-docinfo.xml` right above `<revision>` for `2026-08-28`:

```xml
  <revision>
    <date>2026-09-01</date>
    <revdescription>
     <itemizedlist>
      <listitem>
       <para>Added section <link xlink:href="index.html#jsc-PED-16216">Performance Co-Pilot (PCP) upgraded to version 6.3.8</link> (jsc#PED-16216)</para>
      </listitem>
     </itemizedlist>
    </revdescription>
  </revision>
```

- [ ] **Step 2: Update revdate in SLES 16.1 master document**
In `adoc/sles/release-notes-sles-161.adoc`, replace:
```asciidoc
:revdate: 2026-08-28
```
with:
```asciidoc
:revdate: 2026-09-01
```

- [ ] **Step 3: Run schema validation**
Explain the command and run:
`make validate PRODUCT_VERSION=sles_16.1`
Expected: SUCCESS

---

### Task 3: Commit Changes

**Files:**
- Modify: None (committing files)

**Interfaces:**
- Consumes: All changes from Task 1 and Task 2
- Produces: Clean git history with a single commit

- [ ] **Step 1: Check git status**
Explain the command and run:
`git status`
Expected: Only `version161.adoc`, `release-notes-sles-161-docinfo.xml`, and `release-notes-sles-161.adoc` are modified.

- [ ] **Step 2: Commit with correct commit message**
Explain the command and run:
```bash
git add adoc/sles/version161.adoc adoc/sles/release-notes-sles-161-docinfo.xml adoc/sles/release-notes-sles-161.adoc
git commit -m "SLES 16.1: Add release note for pcp upgrade to version 6.3.8 (jsc#PED-16216)"
```
Expected: SUCCESS
