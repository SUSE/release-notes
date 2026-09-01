# Spec: Performance Co-Pilot (PCP) Upgrade to 6.3.8 Release Note

## 1. Context & Requirements
- **Jira Issue:** [PED-16216](https://jira.suse.com/browse/PED-16216)
- **Product & Version:** SUSE Linux Enterprise Server (SLES) 16.1
- **Goal:** Draft and add a release note for the upgrade of Performance Co-Pilot (PCP) from 6.2.0 to 6.3.8 in SLES 16.1.
- **Conventions:**
  - One sentence per line in AsciiDoc.
  - SLES 16.1 content is monolithic, located under `adoc/sles/version161.adoc`.
  - Update `adoc/sles/release-notes-sles-161-docinfo.xml` revision history `<revhistory>` with a new entry on top.
  - Update `revdate` attribute in `adoc/sles/release-notes-sles-161.adoc` to `2026-09-01`.

## 2. Proposed Changes

### 2.1 adoc/sles/version161.adoc
Add the release note inline under the `== Changes affecting all architectures` section. Let's place it after the `curl` or `patch` updates.

```asciidoc
[#jsc-PED-16216]
=== Performance Co-Pilot (PCP) upgraded to version 6.3.8

Performance Co-Pilot (PCP) has been upgraded from version 6.2.0 to 6.3.8.
This version upgrade introduces AMD GPU metric monitoring support in `pcp-htop`.
It adds Valkey support alongside Redis in `libpcp_web`.
This version upgrade also resolves multiple security vulnerabilities, including CVE-2024-45769 (bsc#1230551).
For a complete list of changes, see the upstream release notes at link:https://pcp.io/[] and the package changelog.
```

### 2.2 adoc/sles/release-notes-sles-161-docinfo.xml
Add a revision block to the top of `<revhistory>`:

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

### 2.3 adoc/sles/release-notes-sles-161.adoc
Update `:revdate: 2026-08-28` to `:revdate: 2026-09-01`.

---

## 3. Verification & Validation Strategy
- Run `make validate PRODUCT_VERSION=sles_16.1` to ensure DAPS and AsciiDoc schema validation passes.
