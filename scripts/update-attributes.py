#!/usr/bin/env python3
import urllib.request
import re
import sys

BASE_URL = "https://raw.githubusercontent.com/openSUSE/doc-kit/refs/heads/main/entities/"
OUTPUT_DIR = "adoc/common/"
OUTPUT_FILE = OUTPUT_DIR + "attributes-generic.adoc"
# Included verbatim by generic-attributes.adoc; copied unmodified.
L10N_FILE = "l10n-generic-attributes.adoc"

COMPATIBILITY_BLOCK = """
// =============================================================================
// BACKWARD-COMPATIBILITY ALIASES & RE-DEFINITIONS FOR RELEASE-NOTES-GITHUB
// =============================================================================

// Doctype must be article for release notes to render section levels correctly
:doctype: article

// Formatting/Structural defaults for release-notes-github
:docinfo:
:toc:
:toc-placement: auto
:toc-title: Table of Contents
:icons:
:lang: en
:numbered:
:show-link-uri:

// Document attributes used across various release notes
:rnotes: Release Notes
:yast2: {yast}2
:we: Workstation Extension

// Products & acronyms remapped or preserved from old attributes-generic
:slessap: {sles4sap}
:slessapa: {sles4sapa}
:slm-short: SL Micro
:slsa: SLES
:slesa: {slsa}
:slda: {sleda}
:haa: {sleha}
:haga: {slehag}

// Userspace Live Patching old variables
:ulpfull: user space live patching
:ulpshort: ULP
:ulp: {ulpshort} ({ulpfull})

// Hardware/Architecture attributes
:ampereone: AmpereOne
:ampereonereg: {ampereone}*
:grace: Grace
:gracehopper: {grace} Hopper
:nvidiagrace: NVIDIA {grace}
:nvidiagracehopper: NVIDIA {gracehopper}
:nvidiagracehopperreg: {nvidiagracehopper}*
:nvidiagracereg: {nvidiagrace}*
:nvidiaorin: NVIDIA {orin}
:nvidiaorinreg: {nvidiaorin}*
:tegra: Tegra
:tegrareg: {tegra}*

// Default lifecycle fallback if empty or undefined
ifndef::lifecycle[]
:lifecycle: unmaintained
endif::[]
ifeval::["{lifecycle}" == ""]
:lifecycle: unmaintained
endif::[]
"""

def fetch(name):
    url = BASE_URL + name
    print(f"Fetching {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        sys.exit(1)

def write(path, content):
    print(f"Writing to {path}...")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"Error writing file: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    content = fetch("generic-attributes.adoc")
    l10n_content = fetch(L10N_FILE)

    processed_lines = []
    lines = content.splitlines()

    for line in lines:
        stripped = line.strip()
        # Comment out doctype: inline
        if stripped.startswith(":doctype: inline"):
            processed_lines.append("// Removed downstream for article/book compatibility:")
            processed_lines.append(f"// {line}")
        # Comment out missing product-attributes include
        elif stripped.startswith((
            "include::../common/product-attributes.adoc[]",
            "include::./product-attributes.adoc[]",
            "include::product-attributes.adoc[]",
        )):
            processed_lines.append("// Removed downstream (not used/present in release-notes-github):")
            processed_lines.append(f"// {line}")
        # Comment out missing network-attributes include
        elif stripped.startswith((
            "include::../common/network-attributes.adoc[]",
            "include::./network-attributes.adoc[]",
            "include::network-attributes.adoc[]",
        )):
            processed_lines.append("// Removed downstream (not used/present in release-notes-github):")
            processed_lines.append(f"// {line}")
        # Move the l10n include to the end: its attributes (for example
        # :nautilus: {gnome} Files) reference attributes defined later in the file,
        # and AsciiDoc resolves references when the attribute is defined.
        elif stripped == f"include::./{L10N_FILE}[]":
            processed_lines.append("// Moved to the end of this file, after the attributes it references:")
            processed_lines.append(f"// {line}")
        else:
            processed_lines.append(line)

    processed_lines.append("")
    processed_lines.append(f"include::./{L10N_FILE}[]")

    processed_content = "\n".join(processed_lines) + "\n" + COMPATIBILITY_BLOCK + "\n"

    write(OUTPUT_FILE, processed_content)
    write(OUTPUT_DIR + L10N_FILE, l10n_content if l10n_content.endswith("\n") else l10n_content + "\n")
    print("Done successfully!")

if __name__ == "__main__":
    main()
