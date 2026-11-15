"""Read-only checks of preinstalled GitHub runner build tools."""

import os
import platform
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import install_rust


@unittest.skipUnless(os.environ.get("GITHUB_ACTIONS") == "true", "GitHub runner check")
class InstalledBuildToolsTests(unittest.TestCase):
    @unittest.skipUnless(platform.system() == "Windows", "Windows runner check")
    def test_msvc_environment_and_microsoft_signature_with_unicode_path(self):
        visual_studio = install_rust._windows_vs_path()
        self.assertIsNotNone(visual_studio)
        environment = install_rust._windows_build_environment(visual_studio)
        self.assertTrue(shutil.which("cl.exe", path=environment["PATH"]))
        self.assertTrue(shutil.which("link.exe", path=environment["PATH"]))
        setup = (Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio"
                 / "Installer" / "setup.exe")
        self.assertTrue(setup.is_file())
        with tempfile.TemporaryDirectory(prefix="Rust 설치 '") as temporary:
            copied = Path(temporary) / "Microsoft setup.exe"
            shutil.copy2(setup, copied)
            install_rust._verify_authenticode(copied)

    @unittest.skipUnless(platform.system() == "Darwin", "macOS runner check")
    def test_macos_command_line_tools_are_detected(self):
        self.assertTrue(install_rust._is_macos_build_ready())


if __name__ == "__main__":
    unittest.main()
