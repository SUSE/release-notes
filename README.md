# SUSE Release Notes

This repository contains release notes for SUSE products.
They are written in [AsciiDoc](https://docs.asciidoctor.org/asciidoc/latest/).

Currently the repository contains release notes for these products:
* SL Micro
  * 6.0
  * 6.1
  * 6.2
* SLE Server/High Availability/for SAP applications
  * 16.0
* openSUSE Leap
  * 16.0


## How to contribute

See [CONTRIBUTING.md](CONTRIBUTING.md).
The latest pre-production build of release-notes can be viewed [here](https://susedoc.github.io/#release-notes).

## Where to add note

The repository structure is like this:

```
adoc/
├── micro/
│   ├── version60.adoc
│   └── version61.adoc
└── another-product/
    ├── versionX.adoc
    └── versionY.adoc
```

If the file for the version doesn't exist, feel free to submit an issue/PR.
