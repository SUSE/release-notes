#!/usr/bin/env python3
import urllib.request
import re
import sys

URL = "https://raw.githubusercontent.com/openSUSE/doc-kit/refs/heads/main/entities/generic-attributes.adoc"
OUTPUT_FILE = "adoc/common/attributes-generic.adoc"

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

def main():
    print(f"Fetching {URL}...")
    try:
        with urllib.request.urlopen(URL) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        sys.exit(1)

    processed_lines = []
    lines = content.splitlines()

    for line in lines:
        stripped = line.strip()
        # Comment out doctype: inline
        if stripped.startswith(":doctype: inline"):
            processed_lines.append("// Removed downstream for article/book compatibility:")
            processed_lines.append(f"// {line}")
        # Comment out missing product-attributes include
        elif stripped.startswith("include::../common/product-attributes.adoc[]"):
            processed_lines.append("// Removed downstream (not used/present in release-notes-github):")
            processed_lines.append(f"// {line}")
        # Comment out missing network-attributes include
        elif stripped.startswith("include::../common/network-attributes.adoc[]"):
            processed_lines.append("// Removed downstream (not used/present in release-notes-github):")
            processed_lines.append(f"// {line}")
        else:
            processed_lines.append(line)

    processed_content = "\n".join(processed_lines) + "\n" + COMPATIBILITY_BLOCK + "\n"

    print(f"Writing to {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(processed_content)
        print("Done successfully!")
    except Exception as e:
        print(f"Error writing file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
