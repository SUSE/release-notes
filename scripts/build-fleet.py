#!/usr/bin/env python3
import os
import sys
import yaml
import shutil
import subprocess

def run_command(cmd):
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        sys.exit(res.returncode)
    return res.stdout

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

    print(f"Orchestrating builds. Target base: {dest_base}")

    # OPTIMIZATION: Clean the build directory exactly ONCE at the start,
    # allowing DAPS to reuse its shared includes compilation cache across products.
    if os.path.exists("build"):
        print("Cleaning previous builds...")
        shutil.rmtree("build")

    # Process each product in the registry
    for dc_file, meta in registry.items():
        # TYPO PROTECTION: If a registered DC file is missing, fail immediately and abort.
        if not os.path.exists(dc_file):
            print(f"Error: Registered configuration file {dc_file} does not exist!", file=sys.stderr)
            sys.exit(1)

        family = meta["family"]
        version = meta["version"]
        doc_name = meta["doc-name"]

        # Compile via Makefile using PRODUCT_VERSION overrides
        prod_version = dc_file.replace("DC-releasenotes_", "")
        run_command(["make", "html", f"PRODUCT_VERSION={prod_version}"])

        # Resolve built DAPS directories
        # Expected: build/releasenotes_<suffix>/html/releasenotes_<suffix>/
        built_base_name = f"releasenotes_{prod_version}"
        src_dir = os.path.join("build", built_base_name, "html", built_base_name)

        if not os.path.exists(src_dir):
            print(f"Error: Build output directory {src_dir} not found.", file=sys.stderr)
            sys.exit(1)

        # Construct target folder matching susedoc URL expectations
        # Schema: <dest_base>/<family>-<version>/html/<doc_name>/
        dest_dir = os.path.join(dest_base, f"{family}-{version}", "html", doc_name)
        os.makedirs(dest_dir, exist_ok=True)

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

    # Clean build folder and replace artifact-dir with publish
    if os.path.exists("artifact-dir"):
        shutil.rmtree("artifact-dir")
    shutil.move("publish", "artifact-dir")
    print("Orchestration successfully finished.")

if __name__ == "__main__":
    main()
