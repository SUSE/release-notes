#!/usr/bin/env python3
import os
import sys
import shutil

def main():
    if not os.path.isdir("docs-artifact-collect"):
        sys.exit(0)

    # Read affected DCs from command-line arguments
    affected_dcs = set(sys.argv[1:])

    print("Filtering staging directory...")
    for format_dir in os.listdir("docs-artifact-collect"):
        format_path = os.path.join("docs-artifact-collect", format_dir)
        if not os.path.isdir(format_path):
            continue

        for doc_dir in os.listdir(format_path):
            doc_path = os.path.join(format_path, doc_dir)
            if not os.path.isdir(doc_path):
                continue

            dc_name = f"DC-{doc_dir}"
            if dc_name not in affected_dcs:
                print(f"Removing unaffected artifact: {doc_path}")
                shutil.rmtree(doc_path)

if __name__ == "__main__":
    main()
