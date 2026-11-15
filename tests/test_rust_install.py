"""Rust installer contract tests without network or host changes."""

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, TRANSLATIONS, translate
from scripts import install_rust


class RustInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = self.root / "native"
        self.native.mkdir()
        (self.native / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
        self.binary = self.native / "target" / "release" / "chzzk-native"
        self.installed_binary = self.native / "bin" / "chzzk-native"

    def test_existing_windows_build_tools_are_repaired_without_winget(self):
        existing = self.root / "VS2022"
        with patch.object(install_rust, "_windows_vs_path", side_effect=[None, existing]), \
                patch.object(install_rust, "_windows_buildtools_path", return_value=existing), \
                patch.object(install_rust.shutil, "which", return_value="winget.exe"), \
                patch.object(install_rust.platform, "machine", return_value="AMD64"), \
                patch.object(install_rust, "_download") as download, \
                patch.object(install_rust, "_verify_authenticode") as verify, \
                patch.object(install_rust, "_command") as command, \
                patch.object(install_rust, "_say"):
            install_rust._install_windows_build_tools("en")
        command.assert_called_once()
        arguments = command.call_args.args[1]
        self.assertEqual(Path(arguments[0]).name, "vs_BuildTools.exe")
        self.assertIn("modify", arguments)
        self.assertEqual(arguments[arguments.index("--installPath") + 1], existing)
        self.assertIn("--norestart", arguments)
        self.assertEqual(command.call_args.kwargs["allowed_returncodes"], (3010,))
        self.assertEqual(download.call_args.args[0],
                         "https://aka.ms/vs/17/release/vs_BuildTools.exe")
        verify.assert_called_once()

    def test_windows_install_denial_does_not_launch_a_second_installer(self):
        with patch.object(install_rust, "_windows_vs_path", return_value=None), \
                patch.object(install_rust, "_windows_buildtools_path", return_value=None), \
                patch.object(install_rust.shutil, "which", return_value="winget.exe"), \
                patch.object(install_rust, "_command",
                             side_effect=subprocess.CalledProcessError(5, ["winget"])), \
                patch.object(install_rust, "_download") as download, \
                patch.object(install_rust, "_say"), \
                self.assertRaises(subprocess.CalledProcessError):
            install_rust._install_windows_build_tools("en")
        download.assert_not_called()

    def test_signature_path_is_data_and_execution_policy_is_unchanged(self):
        path = self.root / "한글 quote's $(not-code).exe"
        with patch.object(install_rust.subprocess, "run") as run:
            install_rust._verify_authenticode(path)
        arguments = run.call_args.args[0]
        self.assertIn("-Command", arguments)
        self.assertNotIn("-File", arguments)
        self.assertNotIn("-ExecutionPolicy", arguments)
        self.assertNotIn("Set-ExecutionPolicy", arguments[-1])
        self.assertNotIn(str(path), arguments[-1])
        self.assertEqual(run.call_args.kwargs["env"]["CHZZK_RUST_VERIFY_PATH"], str(path))
        self.assertIn("-LiteralPath", arguments[-1])
        self.assertIn("Microsoft Corporation", arguments[-1])

    def test_supported_host_triplets(self):
        cases = (
            ("Windows", "AMD64", "x86_64-pc-windows-msvc"),
            ("Windows", "ARM64", "aarch64-pc-windows-msvc"),
            ("Darwin", "x86_64", "x86_64-apple-darwin"),
            ("Darwin", "arm64", "aarch64-apple-darwin"),
            ("Linux", "x86_64", "x86_64-unknown-linux-gnu"),
            ("Linux", "aarch64", "aarch64-unknown-linux-gnu"),
        )
        for system, machine, expected in cases:
            with self.subTest(system=system, machine=machine), \
                    patch.object(install_rust.platform, "system", return_value=system), \
                    patch.object(install_rust.platform, "machine", return_value=machine):
                self.assertEqual(install_rust._host_triplet(), expected)

        for system, machine in (("Linux", "i686"), ("FreeBSD", "x86_64")):
            with self.subTest(system=system, machine=machine), \
                    patch.object(install_rust.platform, "system", return_value=system), \
                    patch.object(install_rust.platform, "machine", return_value=machine):
                self.assertIsNone(install_rust._host_triplet())

    def test_linux_prerequisite_commands_are_selected_by_distro(self):
        cases = (
            ("ubuntu", ["apt-get", "install", "-y", "build-essential"]),
            ("fedora", ["dnf", "install", "-y", "gcc"]),
            ("arch", ["pacman", "-S", "--needed", "--noconfirm", "base-devel"]),
        )
        for distro, expected in cases:
            with self.subTest(distro=distro), \
                    patch.object(install_rust, "_linux_packages_missing",
                                 return_value=[expected[-1]]), \
                    patch.object(install_rust, "_root_command", side_effect=lambda cmd: cmd), \
                    patch.object(install_rust, "_command") as command:
                install_rust._install_linux_prerequisites("en", distro)
            self.assertEqual(command.call_args.args[1], expected)

    def test_linux_rust_packages_use_the_distribution_package_manager(self):
        cases = (
            ("ubuntu", [["apt-get", "update"],
                        ["apt-get", "install", "-y", "rustc", "cargo"]]),
            ("debian", [["apt-get", "update"],
                        ["apt-get", "install", "-y", "rustc", "cargo"]]),
            ("fedora", [["dnf", "install", "-y", "rust", "cargo"]]),
            ("arch", [["pacman", "-S", "--needed", "--noconfirm", "rust"]]),
        )
        for distro, expected in cases:
            with self.subTest(distro=distro), \
                    patch.object(install_rust, "_package_installed", return_value=False), \
                    patch.object(install_rust, "_root_command", side_effect=lambda cmd: cmd), \
                    patch.object(install_rust, "_command") as command:
                install_rust._install_linux_rust("en", distro)
            self.assertEqual([call.args[1] for call in command.call_args_list], expected)

    def test_dpkg_config_files_status_is_not_treated_as_installed(self):
        result = SimpleNamespace(returncode=0, stdout="config-files")
        with patch.object(install_rust.subprocess, "run", return_value=result) as run:
            self.assertFalse(install_rust._package_installed("apt-get", "gcc"))
        self.assertEqual(run.call_args.args[0][0], "dpkg-query")

    def test_arch_gcc_alone_does_not_satisfy_base_devel(self):
        which = lambda name: "/usr/bin/gcc" if name == "cc" else None
        with patch.object(install_rust, "_linux_prerequisites_usable", return_value=False), \
                patch.object(install_rust.shutil, "which", side_effect=which), \
                patch.object(install_rust, "_package_installed", return_value=False), \
                patch.object(Path, "is_file", return_value=False):
            missing = install_rust._linux_packages_missing(
                "arch", "pacman", "base-devel pkgconf openssl ca-certificates"
            )
        self.assertIn("base-devel", missing)

    def test_declining_persists_python_only_marker_without_building(self):
        with patch("builtins.input", return_value="2"), \
                patch.object(install_rust, "_enable") as enable, \
                patch.object(install_rust, "_say"):
            self.assertFalse(install_rust.configure_rust("en", root=self.root))

        self.assertTrue((self.native / ".disabled").is_file())
        enable.assert_not_called()

    def test_unsupported_platform_shows_manual_steps_without_install_commands(self):
        with patch("builtins.input", return_value="1"), \
                patch.object(install_rust.platform, "system", return_value="FreeBSD"), \
                patch.object(install_rust.platform, "machine", return_value="x86_64"), \
                patch.object(install_rust, "_say"), \
                patch.object(install_rust, "_command") as command, \
                patch.object(install_rust, "_download") as download, \
                patch.object(install_rust, "_install_rustup") as rustup:
            self.assertFalse(install_rust.configure_rust("en", root=self.root))

        command.assert_not_called()
        download.assert_not_called()
        rustup.assert_not_called()
        self.assertTrue((self.native / ".disabled").is_file())

    def test_rustup_checksum_mismatch_never_runs_installer(self):
        def download(_url, destination, _limit):
            destination.write_bytes(
                b"0" * 64 + b"  rustup-init\n"
                if destination.name.endswith(".sha256") else b"installer"
            )

        with patch.object(install_rust, "_download", side_effect=download), \
                patch.object(install_rust, "_command") as command, \
                patch.object(install_rust, "_say"), \
                self.assertRaises(install_rust.SetupError):
            install_rust._install_rustup("en", "x86_64-unknown-linux-gnu")

        command.assert_not_called()

    def test_rustup_download_runs_only_after_sha256_matches(self):
        payload = b"verified rustup installer"
        downloads = []

        def download(url, destination, _limit):
            downloads.append(url)
            if destination.name.endswith(".sha256"):
                destination.write_text(hashlib.sha256(payload).hexdigest(), encoding="ascii")
            else:
                destination.write_bytes(payload)

        def command(_language, args, **_kwargs):
            installer = Path(args[0])
            self.assertTrue(installer.is_file())
            if os.name != "nt":
                self.assertTrue(installer.stat().st_mode & 0o111)

        with patch.object(install_rust, "_download", side_effect=download), \
                patch.object(install_rust, "_command", side_effect=command) as run_command, \
                patch.object(install_rust, "_say"):
            install_rust._install_rustup("en", "x86_64-unknown-linux-gnu")

        suffix = ".exe" if os.name == "nt" else ""
        base = ("https://static.rust-lang.org/rustup/dist/"
                f"x86_64-unknown-linux-gnu/rustup-init{suffix}")
        self.assertEqual(downloads, [base, base + ".sha256"])
        args = run_command.call_args.args[1]
        self.assertEqual(Path(args[0]).name, f"rustup-init{suffix}")
        self.assertEqual(tuple(args[1:]), install_rust.RUSTUP_FLAGS)

    def test_empty_or_non_ascii_checksum_fails_setup_and_persists_marker(self):
        for checksum in (b"", b"\xff\xfe"):
            with self.subTest(checksum=checksum), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)

                def download(_url, destination, _limit, checksum=checksum):
                    destination.write_bytes(
                        checksum if destination.name.endswith(".sha256") else b"installer"
                    )

                with patch("builtins.input", return_value="1"), \
                        patch.object(install_rust.platform, "system", return_value="Linux"), \
                        patch.object(install_rust, "_host_triplet",
                                     return_value="x86_64-unknown-linux-gnu"), \
                        patch.object(install_rust, "_read_os_release", return_value="ubuntu"), \
                        patch.object(install_rust, "_install_linux_prerequisites"), \
                        patch.object(install_rust, "_usable_rust", return_value=None), \
                        patch.object(install_rust, "_download", side_effect=download), \
                        patch.object(install_rust, "_command") as command, \
                        patch.object(install_rust, "_say"):
                    self.assertFalse(install_rust.configure_rust("en", root=root))

                command.assert_not_called()
                self.assertTrue((root / "native" / ".disabled").is_file())

    def test_os_release_normalizes_uppercase_distro_id(self):
        with patch.object(install_rust.platform, "freedesktop_os_release",
                          return_value={"ID": "Ubuntu"}):
            self.assertEqual(install_rust._read_os_release(), "ubuntu")

    def test_probe_rejects_boolean_version(self):
        process = SimpleNamespace(
            communicate=lambda *_args, **_kwargs: (
                b'{"version":true,"id":1,"ok":true,"service":"chzzk-native"}', None
            ),
            returncode=0,
        )
        with patch.object(install_rust.subprocess, "Popen", return_value=process), \
                self.assertRaises(install_rust.SetupError):
            install_rust._probe_binary(self.root / "chzzk-native")

    def test_cli_language_defaults_and_explicit_selection(self):
        with patch.object(install_rust, "configure_rust", return_value=False) as configure:
            self.assertEqual(install_rust.main([]), 1)
        configure.assert_called_once_with(DEFAULT_LANGUAGE)

        with patch.object(install_rust, "configure_rust", return_value=False) as configure:
            self.assertEqual(install_rust.main(["--language", "ja"]), 1)
        configure.assert_called_once_with("ja")

    def test_missing_linux_rust_uses_system_package_tools_without_rustup(self):
        commands = []
        paths = {"cargo": Path("/usr/bin/cargo"), "rustc": Path("/usr/bin/rustc")}
        calls = []

        def usable(*, prefer_system=False, **_kwargs):
            calls.append(prefer_system)
            return None if not prefer_system else paths

        def command(_language, args, **_kwargs):
            args = [str(value) for value in args]
            commands.append(args)
            if "build" in args:
                self.binary.parent.mkdir(parents=True, exist_ok=True)
                self.binary.write_bytes(b"new-helper")
            return SimpleNamespace(returncode=0)

        with patch("builtins.input", return_value="1"), \
                patch.object(install_rust.platform, "system", return_value="Linux"), \
                patch.object(install_rust, "_host_triplet",
                             return_value="x86_64-unknown-linux-gnu"), \
                patch.object(install_rust, "_read_os_release", return_value="ubuntu"), \
                patch.object(install_rust, "_install_linux_prerequisites") as prerequisites, \
                patch.object(install_rust, "_usable_rust", side_effect=usable), \
                patch.object(install_rust, "_install_linux_rust") as install_linux_rust, \
                patch.object(install_rust, "_install_rustup") as install_rustup, \
                patch.object(install_rust, "_command", side_effect=command), \
                patch.object(install_rust, "_probe_binary"), \
                patch.object(install_rust, "_say"):
            self.assertTrue(install_rust.configure_rust("en", root=self.root))

        prerequisites.assert_called_once_with("en", "ubuntu")
        install_linux_rust.assert_called_once_with("en", "ubuntu")
        install_rustup.assert_not_called()
        self.assertEqual(calls, [False, True])
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][:3], [str(Path("/usr/bin/cargo")), "build", "--release"])
        self.assertEqual(self.installed_binary.read_bytes(), b"new-helper")

    def test_linux_package_failure_keeps_python_only_marker_without_rustup(self):
        with patch("builtins.input", return_value="1"), \
                patch.object(install_rust.platform, "system", return_value="Linux"), \
                patch.object(install_rust, "_host_triplet",
                             return_value="x86_64-unknown-linux-gnu"), \
                patch.object(install_rust, "_read_os_release", return_value="debian"), \
                patch.object(install_rust, "_install_linux_prerequisites"), \
                patch.object(install_rust, "_usable_rust", return_value=None), \
                patch.object(install_rust, "_install_linux_rust",
                             side_effect=subprocess.CalledProcessError(1, ["apt-get"])), \
                patch.object(install_rust, "_install_rustup") as install_rustup, \
                patch.object(install_rust, "_say"):
            self.assertFalse(install_rust.configure_rust("en", root=self.root))

        install_rustup.assert_not_called()
        self.assertTrue((self.native / ".disabled").is_file())

    def test_missing_macos_rust_still_uses_rustup(self):
        binary = self.root / "native" / "target" / "release" / "chzzk-native"
        commands = []
        paths = {"cargo": Path("/temporary/cargo"), "rustc": Path("/temporary/rustc"),
                 "rustup": Path("/temporary/rustup")}

        def command(_language, args, **_kwargs):
            commands.append([str(value) for value in args])
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_bytes(b"mac-helper")

        with patch.object(install_rust.platform, "system", return_value="Darwin"), \
                patch.object(install_rust, "_host_triplet",
                             return_value="aarch64-apple-darwin"), \
                patch.object(install_rust, "_is_macos_build_ready", return_value=True), \
                patch.object(install_rust, "_usable_rust", return_value=None), \
                patch.object(install_rust, "_install_rustup") as rustup, \
                patch.object(install_rust, "_install_linux_rust") as linux_rust, \
                patch.object(install_rust, "_rust_paths_after_install", return_value=paths), \
                patch.object(install_rust, "_command", side_effect=command), \
                patch.object(install_rust, "_probe_binary"), \
                patch.object(install_rust, "_say"):
            self.assertTrue(install_rust._enable("en", self.root))

        rustup.assert_called_once_with("en", "aarch64-apple-darwin")
        linux_rust.assert_not_called()
        self.assertEqual(commands[0][:3], [str(Path("/temporary/cargo")), "+stable", "build"])

    def test_existing_rust_builds_without_redownloading_rustup(self):
        commands = []

        def command(_language, args, **_kwargs):
            args = [str(value) for value in args]
            commands.append(args)
            self.binary.parent.mkdir(parents=True, exist_ok=True)
            self.binary.write_bytes(b"built-helper")
            return SimpleNamespace(returncode=0)

        with patch.object(install_rust.platform, "system", return_value="Linux"), \
                patch.object(install_rust, "_host_triplet",
                             return_value="x86_64-unknown-linux-gnu"), \
                patch.object(install_rust, "_read_os_release", return_value="debian"), \
                patch.object(install_rust, "_install_linux_prerequisites") as prerequisites, \
                patch.object(install_rust, "_usable_rust",
                             return_value={"cargo": Path("cargo"), "rustc": Path("rustc")}), \
                patch.object(install_rust, "_install_rustup") as install_rustup, \
                patch.object(install_rust, "_rust_paths_after_install") as after_install, \
                patch.object(install_rust, "_command", side_effect=command), \
                patch.object(install_rust, "_probe_binary"), \
                patch.object(install_rust, "_say"):
            self.assertTrue(install_rust._enable("en", self.root))

        prerequisites.assert_called_once_with("en", "debian")
        install_rustup.assert_not_called()
        after_install.assert_not_called()
        self.assertEqual(commands, [[
            "cargo", "build", "--release", "--locked", "--manifest-path",
            str(self.native / "Cargo.toml"),
        ]])

    def test_system_cargo_bin_is_preferred_and_target_dir_is_forced(self):
        cargo_bin = Path("/usr/bin")
        cargo = cargo_bin / "cargo"
        paths = {"cargo": cargo, "rustc": cargo_bin / "rustc"}
        calls = []

        def usable(*, prefer_system=False, **_kwargs):
            calls.append(prefer_system)
            return paths if prefer_system else None

        def command(_language, args, *, env, **_kwargs):
            args = [str(value) for value in args]
            self.assertEqual(args[0], str(cargo))
            self.assertTrue(env["PATH"].startswith(str(cargo_bin) + os.pathsep))
            self.assertEqual(env["CARGO_TARGET_DIR"], str(self.native / "target"))
            self.binary.parent.mkdir(parents=True, exist_ok=True)
            self.binary.write_bytes(b"new-helper")

        inherited_path = os.environ.get("PATH", "")
        with patch.dict(os.environ, {
                "CARGO_TARGET_DIR": str(self.root / "external-target"),
                "PATH": inherited_path,
        }), patch.object(install_rust.platform, "system", return_value="Linux"), \
                patch.object(install_rust, "_host_triplet",
                             return_value="x86_64-unknown-linux-gnu"), \
                patch.object(install_rust, "_read_os_release", return_value="ubuntu"), \
                patch.object(install_rust, "_install_linux_prerequisites"), \
                patch.object(install_rust, "_install_linux_rust"), \
                patch.object(install_rust, "_usable_rust", side_effect=usable), \
                patch.object(install_rust, "_install_rustup"), \
                patch.object(install_rust, "_command", side_effect=command), \
                patch.object(install_rust, "_probe_binary"), \
                patch.object(install_rust, "_say"):
            self.assertTrue(install_rust._enable("en", self.root))

        self.assertEqual(calls, [False, True])

    def test_windows_environment_path_merge_prefers_developer_command_path(self):
        result = SimpleNamespace(stdout="Path=C:\\RustTools;C:\\Windows\r\n")
        with patch.dict(os.environ, {"PATH": "old-path"}), \
                patch.object(install_rust.platform, "machine", return_value="AMD64"), \
                patch.object(install_rust.subprocess, "run", return_value=result):
            env = install_rust._windows_build_environment(self.root)

        self.assertEqual(env["PATH"], "C:\\RustTools;C:\\Windows")

    def test_build_failure_keeps_existing_binary_and_persists_disabled_marker(self):
        self.installed_binary.parent.mkdir(parents=True)
        self.installed_binary.write_bytes(b"old-helper")

        def command(_language, args, **_kwargs):
            if "build" in args:
                raise subprocess.CalledProcessError(1, args)

        with patch("builtins.input", return_value="1"), \
                patch.object(install_rust.platform, "system", return_value="Linux"), \
                patch.object(install_rust, "_host_triplet",
                             return_value="x86_64-unknown-linux-gnu"), \
                patch.object(install_rust, "_read_os_release", return_value="ubuntu"), \
                patch.object(install_rust, "_install_linux_prerequisites"), \
                patch.object(install_rust, "_usable_rust",
                             return_value={"cargo": Path("cargo"), "rustc": Path("rustc")}), \
                patch.object(install_rust, "_command", side_effect=command), \
                patch.object(install_rust, "_publish_binary") as publish, \
                patch.object(install_rust, "_say"):
            self.assertFalse(install_rust.configure_rust("en", root=self.root))

        self.assertEqual(self.installed_binary.read_bytes(), b"old-helper")
        self.assertTrue((self.native / ".disabled").is_file())
        publish.assert_not_called()

    def test_successful_build_publishes_helper_and_clears_disabled_marker(self):
        disabled = self.native / ".disabled"
        disabled.touch()
        self.installed_binary.parent.mkdir(parents=True)
        self.installed_binary.write_bytes(b"old-helper")

        def command(_language, args, **_kwargs):
            if "build" in args:
                self.binary.parent.mkdir(parents=True, exist_ok=True)
                self.binary.write_bytes(b"new-helper")

        with patch("builtins.input", return_value="1"), \
                patch.object(install_rust.platform, "system", return_value="Linux"), \
                patch.object(install_rust, "_host_triplet",
                             return_value="x86_64-unknown-linux-gnu"), \
                patch.object(install_rust, "_read_os_release", return_value="ubuntu"), \
                patch.object(install_rust, "_install_linux_prerequisites"), \
                patch.object(install_rust, "_usable_rust",
                             return_value={"cargo": Path("cargo"), "rustc": Path("rustc")}), \
                patch.object(install_rust, "_command", side_effect=command), \
                patch.object(install_rust, "_probe_binary"), \
                patch.object(install_rust, "_say"):
            self.assertTrue(install_rust.configure_rust("en", root=self.root))

        self.assertFalse(disabled.exists())
        self.assertEqual(self.installed_binary.read_bytes(), b"new-helper")

    def test_rust_install_translation_keys_exist_for_every_locale(self):
        locales = set(SUPPORTED_LANGUAGES)
        keys = {key.removeprefix("rust_install.")
                for key in TRANSLATIONS[next(iter(SUPPORTED_LANGUAGES))]
                if key.startswith("rust_install.")}
        self.assertTrue(keys)
        for language in locales:
            with self.subTest(language=language):
                for key in keys:
                    translation_key = f"rust_install.{key}"
                    self.assertIn(translation_key, TRANSLATIONS[language])
                    self.assertTrue(translate(
                        language, translation_key, command="cmd", url="url",
                        error="error", platform="platform",
                    ))


if __name__ == "__main__":
    unittest.main()
