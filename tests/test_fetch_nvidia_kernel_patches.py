# tests/test_fetch_nvidia_kernel_patches.py
import unittest
from unittest.mock import patch, mock_open, MagicMock
import sys
import os
import importlib.util

script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "fetch-nvidia-kernel-patches.py"))
spec = importlib.util.spec_from_file_location("fetch_nvidia_kernel_patches", script_path)
fnp = importlib.util.module_from_spec(spec)
sys.modules["fetch_nvidia_kernel_patches"] = fnp
spec.loader.exec_module(fnp)

SAMPLE_PATCH_CONTENT = """From: Dev <dev@suse.com>
Date: Wed, 1 Jan 2026 00:00:00 +0000
Subject: [PATCH] soc/tegra: fuse: Register nvmem lookups at probe
Git-commit: 0bbff9ed81654d5f06bfca484681756ee407f924
Patch-mainline: v6.13-rc1
References: jsc#NVIDIA-55 bsc#1272627

This patch registers nvmem lookups at probe.
"""


class TestFetchNvidiaKernelPatches(unittest.TestCase):
    def test_extract_patch_metadata(self):
        with patch("builtins.open", mock_open(read_data=SAMPLE_PATCH_CONTENT)):
            meta = fnp.extract_patch_metadata("patches.suse/sample.patch")
            self.assertEqual(meta["patch"], "patches.suse/sample.patch")
            self.assertEqual(meta["commit"], "0bbff9ed81654d5f06bfca484681756ee407f924")
            self.assertEqual(meta["upstream"], "v6.13-rc1")
            self.assertEqual(meta["references"], "jsc#NVIDIA-55 bsc#1272627")
            self.assertEqual(meta["subject"], "soc/tegra: fuse: Register nvmem lookups at probe")

    def test_extract_header_whitespace(self):
        lines = [
            "  Git-commit: 0bbff9ed81654d5f06bfca484681756ee407f924",
            "\tSubject: [PATCH] test subject"
        ]
        self.assertEqual(fnp.extract_header(lines, "Git-commit:"), "0bbff9ed81654d5f06bfca484681756ee407f924")
        self.assertEqual(fnp.extract_header(lines, "Subject:"), "[PATCH] test subject")

    def test_extract_header_multiline_folding(self):
        lines = [
            "Subject: [PATCH] iommu: Fix NULL group->domain dereference in",
            " something_important_call() when probe fails",
            "Git-commit: 12345"
        ]
        self.assertEqual(
            fnp.extract_header(lines, "Subject:"),
            "[PATCH] iommu: Fix NULL group->domain dereference in something_important_call() when probe fails"
        )
        self.assertEqual(fnp.extract_header(lines, "Git-commit:"), "12345")

    def test_clean_subject(self):
        self.assertEqual(fnp.clean_subject("[PATCH v2 1/3]  soc/tegra:   fix foo "), "soc/tegra: fix foo")

    def test_format_asciidoc_table(self):
        patches = [
            {
                "patch": "patches.suse/sample.patch",
                "commit": "0bbff9ed81654d5f06bfca484681756ee407f924",
                "upstream": "v6.13-rc1",
                "references": "jsc#NVIDIA-55",
                "subject": "soc/tegra: fuse: Register nvmem lookups at probe",
            }
        ]
        adoc = fnp.format_asciidoc(patches)
        self.assertIn('[cols="2,2,3,5", options="header"]', adoc)
        self.assertIn("| Commit | Upstream | Reference | Subject", adoc)
        self.assertIn("`0bbff9ed8165`", adoc)
        self.assertIn("jsc#NVIDIA-55", adoc)
        self.assertIn("soc/tegra: fuse: Register nvmem lookups at probe", adoc)

    def test_format_text(self):
        patches = [
            {
                "patch": "patches.suse/sample.patch",
                "commit": "0bbff9ed81654d5f06bfca484681756ee407f924",
                "upstream": "v6.13-rc1",
                "references": "jsc#NVIDIA-55",
                "subject": "soc/tegra: fuse: Register nvmem lookups at probe",
            }
        ]
        txt = fnp.format_text(patches)
        self.assertIn("0bbff9ed8165", txt)
        self.assertIn("v6.13-rc1", txt)
        self.assertIn("jsc#NVIDIA-55", txt)
        self.assertIn("soc/tegra: fuse: Register nvmem lookups at probe", txt)

    def test_get_series_patches_inline_comments(self):
        diff_output = """--- a/series.conf
+++ b/series.conf
+ # Full line comment in series.conf
+patches.suse/normal.patch
+patches.suse/inline.patch # bsc#1234567 inline comment
+ # Another comment
"""
        mock_res = MagicMock()
        mock_res.stdout = diff_output
        with patch("fetch_nvidia_kernel_patches.git", return_value=mock_res):
            patches = fnp.get_series_patches(".", "base", "target")
            self.assertEqual(patches, ["patches.suse/normal.patch", "patches.suse/inline.patch"])

    def test_get_series_patches_http(self):
        base_series = "patches.suse/base1.patch\npatches.suse/base2.patch\n"
        target_series = "patches.suse/base1.patch\npatches.suse/base2.patch\npatches.suse/nvidia-new.patch # [NVIDIA]\n"

        def mock_fetch(url, **kwargs):
            if "hb=refs/heads/SL-16.1" in url and "SL-16.1-NV" not in url:
                return base_series
            if "hb=refs/heads/SL-16.1-NV" in url:
                return target_series
            return ""

        with patch("fetch_nvidia_kernel_patches.fetch_http_url", side_effect=mock_fetch):
            patches = fnp.get_series_patches_http("https://example.com/git", "SL-16.1", "SL-16.1-NV")
            self.assertEqual(patches, ["patches.suse/nvidia-new.patch"])

    def test_fetch_patch_metadata_http(self):
        with patch("fetch_nvidia_kernel_patches.fetch_http_url", return_value=SAMPLE_PATCH_CONTENT):
            meta = fnp.fetch_patch_metadata_http("https://example.com/git", "SL-16.1-NV", "patches.suse/sample.patch")
            self.assertEqual(meta["patch"], "patches.suse/sample.patch")
            self.assertEqual(meta["commit"], "0bbff9ed81654d5f06bfca484681756ee407f924")
            self.assertEqual(meta["upstream"], "v6.13-rc1")
            self.assertEqual(meta["references"], "jsc#NVIDIA-55 bsc#1272627")
            self.assertEqual(meta["subject"], "soc/tegra: fuse: Register nvmem lookups at probe")


if __name__ == "__main__":
    unittest.main()

