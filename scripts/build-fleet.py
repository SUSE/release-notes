#!/usr/bin/env python3
import os
import sys
import yaml
import shutil

def main():
    registry_path = ".github/product-registry.yml"
    if not os.path.exists(registry_path):
        print(f"Error: {registry_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(registry_path, "r") as f:
        registry = yaml.safe_load(f)

    # Determine preview folder prefix if passed (e.g. 'preview')
    subfolder = sys.argv[1] if len(sys.argv) > 1 else ""
    dest_base = os.path.join("publish", subfolder) if subfolder else "publish"
    redirect_url = sys.argv[2] if len(sys.argv) > 2 else ""

    print(f"Orchestrating folders. Target base: {dest_base}")

    # Locate the single downloaded build artifact directory inside artifact-dir
    artifact_base = "artifact-dir"
    if not os.path.exists(artifact_base):
        print(f"Error: Base artifact directory {artifact_base} does not exist!", file=sys.stderr)
        sys.exit(1)

    # Find the single subdirectory inside artifact-dir (e.g. builds-71fceb7f)
    subdirs = [os.path.join(artifact_base, d) for d in os.listdir(artifact_base) 
               if os.path.isdir(os.path.join(artifact_base, d))]
    
    if not subdirs:
        print("Error: No unzipped build artifact subdirectory found inside artifact-dir!", file=sys.stderr)
        sys.exit(1)
    
    output_dir = subdirs[0]
    print(f"Found build artifact directory: {output_dir}")

    # Process each product in the registry
    for dc_file, meta in registry.items():
        # TYPO PROTECTION: If a registered DC file is missing from the workspace, fail immediately.
        if not os.path.exists(dc_file):
            print(f"Error: Registered configuration file {dc_file} does not exist in workspace!", file=sys.stderr)
            sys.exit(1)

        slug = meta["slug"]
        doc_name = meta["doc-name"]

        # Resolve built DAPS directories from the downloaded artifact
        # Expected suffix: releasenotes_<suffix> (where suffix is the dc_file name minus DC-releasenotes_)
        prod_version = dc_file.replace("DC-releasenotes_", "")
        built_base_name = f"releasenotes_{prod_version}"
        src_dir = os.path.join(output_dir, "html", built_base_name)

        if not os.path.exists(src_dir):
            print(f"Error: Compiled DAPS output directory {src_dir} was not found inside the downloaded artifact!", file=sys.stderr)
            sys.exit(1)

        # Construct target folder matching static Pages URL expectations
        # Schema: <dest_base>/<slug>/html/<doc_name>/
        dest_dir = os.path.join(dest_base, slug, "html", doc_name)
        os.makedirs(dest_dir, exist_ok=True)

        print(f"Organizing {dc_file} -> {dest_dir}")
        # Move compiled static files into target folder
        for item in os.listdir(src_dir):
            shutil.move(os.path.join(src_dir, item), os.path.join(dest_dir, item))

    # Generate SLES 16 SP0 redirect HTML if a redirect URL was specified
    if redirect_url:
        redirect_dir = os.path.join(dest_base, "sles-16_SP0", "html", "release-notes")
        os.makedirs(redirect_dir, exist_ok=True)
        meta_tag = f'<meta http-equiv="refresh" content="0;{redirect_url}">'
        with open(os.path.join(redirect_dir, "index.html"), "w") as f:
            f.write(meta_tag)

    # Clean the old artifact-dir and replace it with our structured publish folder
    shutil.rmtree(artifact_base)
    shutil.move(dest_base, artifact_base)
    
    # Clean up empty parent publish directory if a subfolder was specified
    if subfolder and os.path.exists("publish"):
        os.rmdir("publish")
        
    print("Folder orchestration successfully completed.")

if __name__ == "__main__":
    main()
