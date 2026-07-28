#!/usr/bin/env python3
import os
import sys
import re

def get_dc_main(dc_file):
    """Extract MAIN file path from a DC file."""
    try:
        with open(dc_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip().startswith("MAIN="):
                    # Extract the path, stripping quotes and spaces
                    path = line.split("=", 1)[1].strip()
                    path = re.sub(r"['\"]", "", path)
                    return path
    except Exception:
        pass
    return None

def find_includes(file_path):
    """Find all recursively included files inside an AsciiDoc file."""
    includes = []
    if not os.path.exists(file_path):
        return includes
    
    dir_name = os.path.dirname(file_path)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                # Match line: include::some/path.adoc[...]
                # Ignore lines that start with comment '//' or similar
                clean_line = line.strip()
                if clean_line.startswith("//"):
                    continue
                match = re.search(r"include::([^\[]+)\[", clean_line)
                if match:
                    inc_path = match.group(1).strip()
                    # Resolve relative path
                    resolved = os.path.normpath(os.path.join(dir_name, inc_path))
                    includes.append(resolved)
    except Exception:
        pass
    return includes

def build_dependencies_for_dc(dc_file):
    """Build set of all files a DC file depends on recursively."""
    main_file = get_dc_main(dc_file)
    if not main_file:
        return set()
    
    dependencies = {dc_file, main_file}
    
    # Also add standard docinfo.xml if it exists
    # e.g., adoc/sles/release-notes-sles-160.adoc -> adoc/sles/release-notes-sles-160-docinfo.xml
    base_name, _ = os.path.splitext(main_file)
    docinfo = f"{base_name}-docinfo.xml"
    if os.path.exists(docinfo):
        dependencies.add(docinfo)

    # Recursively traverse includes
    to_visit = [main_file]
    visited = set()
    while to_visit:
        current = to_visit.pop(0)
        if current in visited:
            continue
        visited.add(current)
        
        includes = find_includes(current)
        for inc in includes:
            dependencies.add(inc)
            if inc not in visited:
                to_visit.append(inc)
                
    return dependencies

def main():
    # 1. Gather all DC files in the root folder
    dc_files = [f for f in os.listdir(".") if f.startswith("DC-") and os.path.isfile(f)]
    
    # 2. Build dependency map for each DC file
    dc_deps = {}
    for dc in dc_files:
        dc_deps[dc] = build_dependencies_for_dc(dc)

    # 3. Read changed files from stdin
    changed_files = [line.strip() for line in sys.stdin if line.strip()]
    if not changed_files:
        # No changed files, output nothing
        return

    # 4. Check for "global" file changes that require building everything
    global_triggers = False
    for f in changed_files:
        # If the file is not in adoc/ or a DC file itself, or is Makefile/scripts/workflow
        if not f.startswith("adoc/") and not f.startswith("DC-"):
            global_triggers = True
            break
        if f == "Makefile" or f.startswith(".github/") or f.startswith("scripts/"):
            global_triggers = True
            break

    if global_triggers:
        # Safety fallback: output all DC files
        print(" ".join(sorted(dc_files)))
        return

    # 5. Map changed files to affected DC files
    affected_dcs = set()
    for changed in changed_files:
        norm_changed = os.path.normpath(changed)
        for dc, deps in dc_deps.items():
            # Check if normalized changed file is in normalized deps
            if any(os.path.normpath(dep) == norm_changed for dep in deps):
                affected_dcs.add(dc)

    if affected_dcs:
        print(" ".join(sorted(affected_dcs)))

if __name__ == "__main__":
    main()
