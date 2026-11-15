"""Read-only checks of preinstalled GitHub runner build tools."""

import os
import platform
import shutil
import subprocess
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
        with tempfile.TemporaryDirectory(prefix="rust-signature-") as temporary, \
                tempfile.TemporaryDirectory(prefix="Rust 설치 '") as unicode_directory:
            setup = Path(temporary) / "vs_BuildTools.exe"
            install_rust._download("https://aka.ms/vs/17/release/vs_BuildTools.exe",
                                   setup, 100 * 1024 * 1024)
            copied = Path(unicode_directory) / "Microsoft setup.exe"
            shutil.copy2(setup, copied)
            for binary in (setup, copied):
                try:
                    install_rust._verify_authenticode(binary)
                except subprocess.CalledProcessError:
                    environment = os.environ.copy()
                    environment["CHZZK_RUST_VERIFY_PATH"] = str(binary)
                    diagnostic = subprocess.run(
                        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                         ("$s=Get-AuthenticodeSignature -LiteralPath $env:CHZZK_RUST_VERIFY_PATH; "
                         "@{status=[string]$s.Status;publisher=$s.SignerCertificate.Subject} "
                         "| ConvertTo-Json -Compress")],
                        env=environment, capture_output=True, check=False, timeout=30,
                    )
                    self.fail("Official bootstrapper signature rejected: "
                              + diagnostic.stdout.decode("utf-8", errors="replace"))
            unsigned = Path(temporary) / "unsigned.exe"
            unsigned.write_bytes(b"unsigned test fixture")
            with self.assertRaises(subprocess.CalledProcessError):
                install_rust._verify_authenticode(unsigned)

    @unittest.skipUnless(platform.system() == "Darwin", "macOS runner check")
    def test_macos_command_line_tools_are_detected(self):
        self.assertTrue(install_rust._is_macos_build_ready())


if __name__ == "__main__":
    unittest.main()
