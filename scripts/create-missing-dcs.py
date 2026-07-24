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

def main():
    attribute_files = glob.glob("adoc/*/*/attributes-generic.adoc")
    print(f"Scanning {len(attribute_files)} directories...")
    
    created_count = 0
    existing_count = 0
    
    for attr_file in sorted(attribute_files):
        # adoc/<product>/<version>/attributes-generic.adoc
        parts = attr_file.split(os.sep)
        if len(parts) < 4:
            continue
        product = parts[1]
        version = parts[2]
        
        # Map product
        prod_map = {
            "sled": "sled",
            "sleha": "sle-ha",
            "slehpc": "sle-hpc",
            "sles": "sles",
            "slesap": "sles-sap"
        }
        mapped_prod = prod_map.get(product, product)
        
        # Format version
        # e.g., "15sp2" -> "15-SP2", "12sp5" -> "12-SP5"
        if "sp" in version:
            v_parts = version.split("sp")
            mapped_ver = f"{v_parts[0]}-SP{v_parts[1].upper()}"
        else:
            mapped_ver = version.upper()
            
        dc_filename = f"DC-releasenotes_{mapped_prod}_{mapped_ver}"
        main_path = os.path.join("adoc", product, version, "release-notes.adoc")
        
        if os.path.exists(dc_filename):
            print(f"File {dc_filename} already exists.")
            existing_count += 1
        else:
            print(f"Creating {dc_filename}...")
            content = TEMPLATE.format(main_path=main_path)
            with open(dc_filename, "w", encoding="utf-8") as f:
                f.write(content)
            created_count += 1
            
    print(f"Done. Created {created_count} DC files. {existing_count} DC files already existed.")

if __name__ == "__main__":
    main()
