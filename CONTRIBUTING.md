# Summary

1. Fork the repository.
2. Make your changes to the "main" branch (there are no other branches)
    1. Write one sentence per line.
    2. If there is a related issue, use its Jira or Bugzilla identifier as the section ID (`[#jsc-SLE-1234]`), or if that is not possible, add it as a comment (`// jsc#SLE-1234`).
3. Submit the changes as a pull request.


# Examples

These are written in [AsciiDoc](#source-format).

## Single paragraph (solution only)

```asciidoc	
[#jsc-SLE-3038]
==== Running XenStore in stubdom
 
Since Xen 4.9, you can easily configure XenStore to run in a `stubdom` instead of Dom0.
This has the advantage that a high Dom0 load no longer affects XenStore performance.
It is a prerequisite to being able to restart Dom0 without having to restart other guests.
```

## Challenge/solution style
```asciidoc	
[#jsc-SLE-3069]
==== QED image format no longer supported
 
The QEMU virtual disk image format is no longer supported.
 
Existing virtual disks using this format can still be accessed, but should be converted to a RAW or QCOW2 format if possible.
Using the QED format for new disks is not supported.
```

# More information on writing notes

## Source format

The release notes are written using AsciiDoc. See the [AsciiDoc documentation](https://asciidoctor.org/docs/asciidoc-writers-guide/) for more information.

## Style

* SUSE Documentation Style Guide at [https://documentation.suse.com/style/](https://documentation.suse.com/style/)
* AsciiDoc Best Practices at [https://asciidoctor.org/docs/asciidoc-recommended-practices/](https://asciidoctor.org/docs/asciidoc-recommended-practices/)

## Types

* Titled notes
    * title and body text
* Collection notes
    * title and individual list items, usually minor changes
* Support tables/lists
    * title and table/list

## Content

* note ID - must be unique within the document
    * For AsciiDoc `[#my-id]`
    * Reference external issues:
        * For Bugzilla, `[#bsc-00000]`
        * For SUSE Jira, `[#jsc-XXX-0000]`
    * If note is not titled, use comment
* information
    * Title
    * Issue description/previous situation (optional)
    * Solution/current situation

## Order

* TABLES/LISTS: at the bottom.
* MINOR CHANGES: above tables but otherwise at the bottom.
* TITLED NOTE:
    * _before the release_
        * the most important first
        * additions before removals
    * _after the release_:
        * at the top

## Commit messages
* Ideally one commit per release note
* Reference external issue
    * For example: `Add note about failing AutoYaST upgrade (bsc#00000)` or `Add note about failing AutoYaST upgrade (jsc#XXX-0000)`

## Working locally

Make sure to pass PRODUCT_VERSION= which needs to match relevant DC-release-notes-$PRODUCT_VERSION in the checkout.
Following example is for DC-releasenotes_leap_160

* Run `make validate PRODUCT_VERSION=leap_16.0` to check for errors
* Run `make html PRODUCT_VERSION=leap_16.0` to see your changes
    * Replace `html` with a different format (`pdf`, `single-html`, `text`) or `all` to generate other formats

# Creating a bug report

Use the Issue Tracker: [Create new issue](https://github.com/SUSE/release-notes/issues/new/choose)

