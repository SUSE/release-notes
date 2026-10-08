# tests/test_fetch_nvidia_kernel_patches.py
import pytest
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

def test_extract_patch_metadata():
    with patch("builtins.open", mock_open(read_data=SAMPLE_PATCH_CONTENT)):
        meta = fnp.extract_patch_metadata("patches.suse/sample.patch")
        assert meta["patch"] == "patches.suse/sample.patch"
        assert meta["commit"] == "0bbff9ed81654d5f06bfca484681756ee407f924"
        assert meta["upstream"] == "v6.13-rc1"
        assert meta["references"] == "jsc#NVIDIA-55 bsc#1272627"
        assert meta["subject"] == "soc/tegra: fuse: Register nvmem lookups at probe"

def test_extract_header_whitespace():
    lines = [
        "  Git-commit: 0bbff9ed81654d5f06bfca484681756ee407f924",
        "\tSubject: [PATCH] test subject"
    ]
    assert fnp.extract_header(lines, "Git-commit:") == "0bbff9ed81654d5f06bfca484681756ee407f924"
    assert fnp.extract_header(lines, "Subject:") == "[PATCH] test subject"

def test_clean_subject():
    assert fnp.clean_subject("[PATCH v2 1/3]  soc/tegra:   fix foo ") == "soc/tegra: fix foo"

def test_format_asciidoc_table():
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
    assert "[cols=\"2,2,3,5\", options=\"header\"]" in adoc
    assert "| Commit | Upstream | Reference | Subject" in adoc
    assert "`0bbff9ed8165`" in adoc
    assert "jsc#NVIDIA-55" in adoc
    assert "soc/tegra: fuse: Register nvmem lookups at probe" in adoc

def test_format_text():
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
    assert "0bbff9ed8165" in txt
    assert "v6.13-rc1" in txt
    assert "jsc#NVIDIA-55" in txt
    assert "soc/tegra: fuse: Register nvmem lookups at probe" in txt

def test_get_series_patches_inline_comments():
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
        assert patches == ["patches.suse/normal.patch", "patches.suse/inline.patch"]
