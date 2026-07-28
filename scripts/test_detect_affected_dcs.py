#!/usr/bin/env python3
import unittest
import sys
import os
import subprocess

class TestDependencyTracer(unittest.TestCase):
    def test_script_exists(self):
        self.assertTrue(os.path.exists("scripts/detect-affected-dcs.py"))

    def test_global_fallback_makefile(self):
        # Makefile edit must trigger all DC files
        proc = subprocess.run(
            [sys.executable, "scripts/detect-affected-dcs.py"],
            input="Makefile\n",
            capture_output=True,
            text=True
        )
        output = proc.stdout.strip()
        # Output must contain multiple DC files (e.g. SLES, SLED, etc.)
        self.assertIn("DC-releasenotes_sles_16.0", output)
        self.assertIn("DC-releasenotes_sles-sap_16.0", output)

    def test_specific_sles_160_edit(self):
        # Editing SLES 16.0 master .adoc should trigger sles_16.0
        proc = subprocess.run(
            [sys.executable, "scripts/detect-affected-dcs.py"],
            input="adoc/sles/release-notes-sles-160.adoc\n",
            capture_output=True,
            text=True
        )
        output = proc.stdout.strip().split()
        self.assertIn("DC-releasenotes_sles_16.0", output)

    def test_recursive_sles_160_includes(self):
        # SLES 16.0 includes version160.adoc. Let's test that editing version160.adoc triggers sles_16.0 and sles-sap_16.0 (due to SLES-SAP includes)
        proc = subprocess.run(
            [sys.executable, "scripts/detect-affected-dcs.py"],
            input="adoc/sles/version160.adoc\n",
            capture_output=True,
            text=True
        )
        output = proc.stdout.strip().split()
        self.assertIn("DC-releasenotes_sles_16.0", output)
        self.assertIn("DC-releasenotes_sles-sap_16.0", output)

if __name__ == "__main__":
    unittest.main()
