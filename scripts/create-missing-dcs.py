#!/usr/bin/env python3
import glob
import os

TEMPLATE = """MAIN={main_path}
ADOC_POST=yes
ADOC_TYPE=article
ADOC_POST_STYLE=adoc_postprocess.xsl
STYLEROOT=/usr/share/xml/docbook/stylesheet/suse2022-ns
XSLTPARAM="--stringparam \\"homepage=https://documentation.suse.com/\\""
XSLTPARAM+="--stringparam \\"overview-page=https://documentation.suse.com/releasenotes/\\""
XSLTPARAM+="--stringparam \\"overview-page-title=Back\\ to\\ Release\\ Notes\\ for\\ SUSE\\ products\\""
"""

REGISTRY_PATH = ".github/product-registry.yml"

def main():
    attribute_files = glob.glob("adoc/*/*/attributes-generic.adoc")
    print(f"Scanning {len(attribute_files)} directories...")
    
    created_count = 0
    existing_count = 0
    registered_count = 0
    
    # Read existing product registry to check for existing registrations
    registry_content = ""
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry_content = f.read()
            
    new_registrations = []
    
    for attr_file in sorted(attribute_files):
        # adoc/<product>/<version>/attributes-generic.adoc
        parts = attr_file.split(os.sep)
        if len(parts) < 4:
            continue
        product = parts[1]
        version = parts[2]
        
        # Map product
        prod_map = {
            "sled": ("sled", "SLED"),
            "sleha": ("sle-ha", "SLE HA"),
            "slehpc": ("sle-hpc", "SLE HPC"),
            "sles": ("sles", "SLES"),
            "slesap": ("sles-sap", "SLES for SAP")
        }
        mapped_prod, short_name = prod_map.get(product, (product, product.upper()))
        
        # Format version
        # e.g., "15sp2" -> "15-SP2", "12sp5" -> "12-SP5"
        if "sp" in version:
            v_parts = version.split("sp")
            mapped_ver = f"{v_parts[0]}-SP{v_parts[1].upper()}"
            ver_display = f"{v_parts[0]} SP{v_parts[1].upper()}"
        else:
            mapped_ver = version.upper()
            ver_display = version.upper()
            
        dc_product_map = {
            "sled": "sled",
            "sleha": "sle-ha",
            "slehpc": "sle-hpc",
            "sles": "sles",
            "slesap": "sles-sap"
        }
        dc_prod = dc_product_map.get(product, product)
        dc_filename = f"DC-releasenotes_{dc_prod}_{mapped_ver}"
        main_path = os.path.join("adoc", product, version, "release-notes.adoc")
        
        # 1. Create DC file if missing
        if os.path.exists(dc_filename):
            existing_count += 1
        else:
            print(f"Creating {dc_filename}...")
            content = TEMPLATE.format(main_path=main_path)
            with open(dc_filename, "w", encoding="utf-8") as f:
                f.write(content)
            created_count += 1
            
        # 2. Register in product-registry.yml if missing
        if f"{dc_filename}:" not in registry_content:
            print(f"Registering {dc_filename} in product registry...")
            # Formulate the YAML entry block
            # e.g. "sled" -> slug is "sled-15-sp2"
            slug_prod = "sleha" if product == "sleha" else ("slehpc" if product == "slehpc" else ("slesap" if product == "slesap" else product))
            slug = f"{slug_prod}-{version.replace('sp', '-sp')}"
            
            entry = f"""{dc_filename}:
  doc-name: release-notes
  short-name: {short_name}
  slug: {slug}
  version: '{ver_display}'
"""
            new_registrations.append(entry)
            registered_count += 1
            
    # Append any new registrations to .github/product-registry.yml
    if new_registrations:
        # Ensure registry file ends with newline before appending
        if registry_content and not registry_content.endswith("\n"):
            registry_content += "\n"
        with open(REGISTRY_PATH, "a", encoding="utf-8") as f:
            for entry in new_registrations:
                f.write(entry)
                
    print(f"Done. Created {created_count} DC files ({existing_count} already existed).")
    print(f"Registered {registered_count} new targets in {REGISTRY_PATH}.")

if __name__ == "__main__":
    main()
