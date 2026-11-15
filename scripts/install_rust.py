"""Offer and install the optional Rust helper for the current user."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, translate

RUST_INSTALL_URL = "https://rust-lang.org/tools/install"
RUSTUP_BASE_URL = "https://static.rust-lang.org/rustup/dist"
RUSTUP_FLAGS = ("-y", "--profile", "minimal", "--default-toolchain", "stable",
                "--no-modify-path")
BUILD_FLAGS = ("build", "--release", "--locked", "--manifest-path")
MANUAL_BUILD = "cargo build --release --locked --manifest-path native/Cargo.toml"
LINUX_PACKAGES = {
    "ubuntu": ("apt-get", "build-essential pkg-config libssl-dev ca-certificates"),
    "debian": ("apt-get", "build-essential pkg-config libssl-dev ca-certificates"),
    "fedora": (
        "dnf", "gcc gcc-c++ make pkgconf-pkg-config openssl-devel ca-certificates"
    ),
    "arch": ("pacman", "base-devel pkgconf openssl ca-certificates"),
    "archlinux": ("pacman", "base-devel pkgconf openssl ca-certificates"),
}
LINUX_RUST_PACKAGES = {
    "ubuntu": ("rustc", "cargo"),
    "debian": ("rustc", "cargo"),
    "fedora": ("rust", "cargo"),
    "arch": ("rust",),
    "archlinux": ("rust",),
}


class SetupError(Exception):
    """A setup failure that has a localized user-facing explanation."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _say(language, key, **values):
    print(translate(language, f"rust_install.{key}", **values), flush=True)


def _command(language, command, *, cwd=None, env=None, timeout=None,
             allowed_returncodes=()):
    _say(language, "command", command=subprocess.list2cmdline(list(map(str, command))))
    result = subprocess.run(
        list(map(str, command)), cwd=cwd, env=env, check=False, timeout=timeout
    )
    if result.returncode and result.returncode not in allowed_returncodes:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result


def _rust_paths(*, prefer_cargo_home=False, prefer_system=False):
    home = Path(os.environ.get("CARGO_HOME") or
                os.environ.get("USERPROFILE") or Path.home())
    cargo_home = (Path(os.environ["CARGO_HOME"]) if os.environ.get("CARGO_HOME")
                  else home / ".cargo")
    suffix = ".exe" if os.name == "nt" else ""
    for name in ("rustup", "cargo", "rustc"):
        found = shutil.which(name)
        if found:
            found = Path(found)
        candidate = cargo_home / "bin" / f"{name}{suffix}"
        system_path = Path("/usr/bin") / f"{name}{suffix}"
        if prefer_system and system_path.is_file():
            yield name, system_path
        if prefer_cargo_home and candidate.is_file():
            yield name, candidate
        if found:
            yield name, found
        if not prefer_cargo_home and candidate.is_file():
            yield name, candidate


def _usable_rust(*, prefer_cargo_home=False, prefer_system=False):
    paths = {}
    for name, path in _rust_paths(prefer_cargo_home=prefer_cargo_home,
                                  prefer_system=prefer_system):
        paths.setdefault(name, path)
    if not all(name in paths for name in ("cargo", "rustc")):
        return None
    try:
        for name in ("cargo", "rustc"):
            subprocess.run([paths[name], "--version"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return paths


def _host_triplet():
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x64": "x86_64", "arm64": "aarch64"}.get(
        machine, machine
    )
    if system == "windows":
        suffix = "pc-windows-msvc"
    elif system == "darwin":
        suffix = "apple-darwin"
    elif system == "linux":
        suffix = "unknown-linux-gnu"
    else:
        return None
    if arch not in {"x86_64", "aarch64"}:
        return None
    return f"{arch}-{suffix}"


def _read_os_release():
    try:
        return platform.freedesktop_os_release().get("ID", "").lower()
    except OSError:
        return ""


def _is_macos_build_ready():
    try:
        subprocess.run(["xcode-select", "-p"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=10)
        subprocess.run(["clang", "--version"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=10)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _install_macos_tools(language):
    _command(language, ["xcode-select", "--install"])
    _say(language, "mac_wait")
    input()
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        if _is_macos_build_ready():
            return
        time.sleep(5)
    raise SetupError("compiler")


def _linux_prerequisites_usable(manager):
    compiler = all(shutil.which(tool) for tool in ("cc", "c++", "make"))
    pkg_config = shutil.which("pkg-config")
    openssl = False
    if pkg_config:
        result = subprocess.run([pkg_config, "--exists", "openssl"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, check=False)
        openssl = result.returncode == 0
    if manager == "pacman":
        ca_bundle = Path("/etc/ssl/certs/ca-certificates.crt").is_file()
    else:
        ca_bundle = any(Path(path).is_file() for path in (
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/pki/tls/certs/ca-bundle.crt",
        ))
    return compiler and pkg_config and openssl and ca_bundle


def _package_installed(manager, package):
    queries = {
        "apt-get": ["dpkg-query", "-W", "-f=${db:Status-Status}", package],
        "dnf": ["rpm", "-q", package],
        "pacman": ["pacman", "-Q", package],
    }
    result = subprocess.run(queries[manager], capture_output=True, text=True,
                            timeout=15, check=False)
    if result.returncode:
        return False
    return result.stdout.strip() == "installed" if manager == "apt-get" else True


def _linux_packages_missing(distro, manager, packages):
    if _linux_prerequisites_usable(manager):
        return []
    missing = []
    if not all(shutil.which(tool) for tool in ("cc", "c++", "make")):
        package = "base-devel" if manager == "pacman" else (
            "build-essential" if manager == "apt-get" else "gcc"
        )
        if not _package_installed(manager, package):
            missing.append(package)
        if manager == "dnf":
            missing.extend(package for package in ("gcc-c++", "make")
                           if not _package_installed(manager, package))
    if not shutil.which("pkg-config"):
        package = "pkgconf" if manager == "pacman" else (
            "pkg-config" if manager == "apt-get" else "pkgconf-pkg-config"
        )
        if not _package_installed(manager, package):
            missing.append(package)
    if not _linux_prerequisites_usable(manager) and not any(
            Path(path).is_file() for path in (
                "/usr/include/openssl/ssl.h", "/usr/include/openssl/opensslv.h"
            )):
        package = "libssl-dev" if manager == "apt-get" else (
            "openssl-devel" if manager == "dnf" else "openssl"
        )
        if not _package_installed(manager, package):
            missing.append(package)
    if manager == "pacman":
        ca_bundle = Path("/etc/ssl/certs/ca-certificates.crt").is_file()
    else:
        ca_bundle = any(Path(path).is_file() for path in (
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/pki/tls/certs/ca-bundle.crt",
        ))
    if not ca_bundle and not _package_installed(manager, "ca-certificates"):
        missing.append("ca-certificates")
    return list(dict.fromkeys(missing))


def _root_command(command):
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return command
    if not shutil.which("sudo"):
        raise SetupError("admin")
    return ["sudo", *command]


def _install_linux_prerequisites(language, distro):
    manager, packages = LINUX_PACKAGES[distro]
    missing = _linux_packages_missing(distro, manager, packages)
    _install_linux_packages(language, manager, missing)


def _install_linux_packages(language, manager, packages):
    if not packages:
        return
    if manager == "apt-get":
        _command(language, _root_command([manager, "update"]))
        command = [manager, "install", "-y", *packages]
    elif manager == "dnf":
        command = [manager, "install", "-y", *packages]
    else:
        command = [manager, "-S", "--needed", "--noconfirm", *packages]
    _command(language, _root_command(command))


def _install_linux_rust(language, distro):
    manager = LINUX_PACKAGES[distro][0]
    missing = [package for package in LINUX_RUST_PACKAGES[distro]
               if not _package_installed(manager, package)]
    _install_linux_packages(language, manager, missing)


def _vswhere():
    default = os.path.expandvars(
        r"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
    )
    candidates = [shutil.which("vswhere.exe"),
                  default]
    return next((Path(item) for item in candidates
                 if item and Path(item).is_file()), None)


def _windows_vs_path():
    vswhere = _vswhere()
    if not vswhere:
        return None
    target_arch = (
        "arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "x64"
    )
    requires = (["Microsoft.VisualStudio.Component.VC.Tools.ARM64"]
                if target_arch == "arm64" else
                ["Microsoft.VisualStudio.Component.VC.Tools.x86.x64"])
    try:
        result = subprocess.run(
            [vswhere, "-latest", "-products", "*", "-requires", *requires,
             "-property", "installationPath"], check=True, capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    path = Path(result.stdout.strip())
    tools = path / "VC" / "Tools" / "MSVC"
    sdk_roots = [Path(value) / "Include" for value in (
        os.environ.get("WindowsSdkDir", ""),
        os.path.expandvars(r"%ProgramFiles(x86)%\Windows Kits\10"),
    ) if value]
    compiler_dirs = [version / "bin" / "Hostx64" / target_arch
                     for version in tools.glob("*")]
    if target_arch == "arm64":
        compiler_dirs.extend(version / "bin" / "Hostarm64" / target_arch
                             for version in tools.glob("*"))
    if (not path.is_dir() or not any(
            (compiler / "cl.exe").is_file() and (compiler / "link.exe").is_file()
            for compiler in compiler_dirs
    )
            or not any(any(sdk.glob("10.0.*")) for sdk in sdk_roots)):
        return None
    return path


def _windows_buildtools_path():
    vswhere = _vswhere()
    if not vswhere:
        return None
    try:
        result = subprocess.run(
            [vswhere, "-latest", "-version", "[17.0,18.0)", "-products",
             "Microsoft.VisualStudio.Product.BuildTools", "-property",
             "installationPath"], check=True, capture_output=True, text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    path = Path(result.stdout.strip())
    return path if path.is_dir() else None


def _verify_authenticode(path):
    script = ("param([string]$Path)\n"
              "$s = Get-AuthenticodeSignature -LiteralPath $Path\n"
              "if ($s.Status -ne 'Valid' -or -not $s.SignerCertificate) { exit 1 }\n"
              "$n = $s.SignerCertificate.GetNameInfo("
              "[System.Security.Cryptography.X509Certificates.X509NameType]"
              "::SimpleName, $false)\n"
              "if ($n -ne 'Microsoft Corporation') { exit 1 }\n")
    with tempfile.TemporaryDirectory(prefix="chzzk-signature-") as directory:
        verifier = Path(directory) / "verify.ps1"
        verifier.write_bytes(b"\xef\xbb\xbf" + script.encode("ascii"))
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                        "-File", str(verifier), str(path)], check=True,
                       timeout=30, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)


def _install_windows_build_tools(language):
    if _windows_vs_path():
        return
    existing = _windows_buildtools_path()
    winget = shutil.which("winget.exe") or shutil.which("winget")
    if winget and not existing:
        _say(language, "windows_uac")
        override = (
            "--passive --wait --norestart --add "
            "Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
        )
        if platform.machine().lower() in {"arm64", "aarch64"}:
            override += " --add Microsoft.VisualStudio.Component.VC.Tools.ARM64"
        _command(language, [winget, "install", "--exact", "--id",
                           "Microsoft.VisualStudio.2022.BuildTools", "--source",
                           "winget",
                           "--accept-source-agreements", "--accept-package-agreements",
                           "--override", override],
                           timeout=3600)
        if _windows_vs_path():
            return
        existing = _windows_buildtools_path()
    url = "https://aka.ms/vs/17/release/vs_BuildTools.exe"
    with tempfile.TemporaryDirectory(prefix="chzzk-vs-") as directory:
        installer = Path(directory) / "vs_BuildTools.exe"
        _say(language, "windows_uac")
        _download(url, installer, 500 * 1024 * 1024)
        _verify_authenticode(installer)
        existing = _windows_buildtools_path()
        if existing:
            command = [installer, "modify", "--passive", "--wait", "--norestart",
                       "--installPath", existing, "--add",
                       "Microsoft.VisualStudio.Workload.VCTools",
                       "--includeRecommended"]
        else:
            command = [installer, "--passive", "--wait", "--norestart", "--add",
                       "Microsoft.VisualStudio.Workload.VCTools",
                       "--includeRecommended"]
        if platform.machine().lower() in {"arm64", "aarch64"}:
            command.extend([
                "--add", "Microsoft.VisualStudio.Component.VC.Tools.ARM64"
            ])
        _command(language, command, timeout=3600, allowed_returncodes=(3010,))
    if not _windows_vs_path():
        raise SetupError("compiler")


def _download(url, destination, limit):
    request = urllib.request.Request(url, headers={"User-Agent": "Chzzk-Rekoda"})
    with urllib.request.urlopen(request, timeout=60) as response, \
            destination.open("wb") as output:
        total = 0
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise SetupError("download")
            output.write(chunk)


def _install_rustup(language, host):
    suffix = ".exe" if os.name == "nt" else ""
    base = f"{RUSTUP_BASE_URL}/{host}/rustup-init{suffix}"
    with tempfile.TemporaryDirectory(prefix="chzzk-rustup-") as directory:
        installer = Path(directory) / f"rustup-init{suffix}"
        checksum_file = Path(directory) / "rustup-init.sha256"
        _download(base, installer, 100 * 1024 * 1024)
        _download(f"{base}.sha256", checksum_file, 4096)
        installer.chmod(installer.stat().st_mode | stat.S_IXUSR)
        try:
            expected = checksum_file.read_text(encoding="ascii").split()[0]
        except (OSError, UnicodeError, IndexError) as error:
            raise SetupError("checksum") from error
        digest = hashlib.sha256(installer.read_bytes()).hexdigest()
        if (len(expected) != 64
                or any(c not in "0123456789abcdefABCDEF" for c in expected)
                or digest != expected.lower()):
            raise SetupError("checksum")
        _command(language, [installer, *RUSTUP_FLAGS], timeout=1800)


def _rust_paths_after_install():
    paths = _usable_rust(prefer_cargo_home=True)
    if not paths:
        raise SetupError("tools")
    return paths


def _windows_build_environment(vs_path):
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    devcmd = vs_path / "Common7" / "Tools" / "VsDevCmd.bat"
    result = subprocess.run(
        ["cmd.exe", "/d", "/u", "/s", "/c",
         f'call "{devcmd}" -arch={arch} >nul && set'],
        check=True, capture_output=True, text=True, encoding="utf-16le",
        errors="replace", timeout=60,
    )
    env = os.environ.copy()
    for line in result.stdout.splitlines():
        line = line.lstrip("\ufeff")
        key, separator, value = line.partition("=")
        if separator and key:
            env[key.upper()] = value
    return env


def _probe_binary(binary):
    process = subprocess.Popen(
        [str(binary), "serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        stdout, _ = process.communicate(
            b'{"version":1,"id":1,"op":"hello"}\n', timeout=5
        )
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise SetupError("probe")
    try:
        reply = json.loads(stdout.splitlines()[0])
    except (IndexError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SetupError("probe") from error
    if (process.returncode != 0 or not isinstance(reply, dict)
            or type(reply.get("version")) is not int or reply.get("version") != 1
            or type(reply.get("id")) is not int or reply.get("id") != 1
            or reply.get("ok") is not True
            or reply.get("service") != "chzzk-native"):
        raise SetupError("probe")


def _publish_binary(binary, native_dir):
    target_dir = native_dir / "bin"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / binary.name
    with tempfile.NamedTemporaryFile(dir=target_dir, prefix=".chzzk-native-",
                                     delete=False) as temporary:
        temp_path = Path(temporary.name)
    try:
        shutil.copyfile(binary, temp_path)
        shutil.copymode(binary, temp_path)
        os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)


def _manual(language, platform_name):
    _say(language, "manual", url=RUST_INSTALL_URL, command=MANUAL_BUILD)
    _say(language, "unsupported", platform=platform_name)


def _enable(language, root):
    if not (root / "native" / "Cargo.toml").is_file():
        raise SetupError("build")
    host = _host_triplet()
    system = platform.system().lower()
    distro = None
    if not host:
        _manual(language, f"{system or 'unknown'} {platform.machine()}")
        return False
    if system == "linux":
        distro = _read_os_release()
        if distro not in LINUX_PACKAGES:
            _manual(language, f"Linux ({distro or 'unknown distribution'})")
            return False
        _install_linux_prerequisites(language, distro)
    elif system == "darwin" and not _is_macos_build_ready():
        _install_macos_tools(language)
    elif system == "windows":
        _install_windows_build_tools(language)

    paths = _usable_rust()
    new_rustup = False
    if not paths and system == "linux":
        _install_linux_rust(language, distro)
        paths = _usable_rust(prefer_system=True)
        if not paths:
            raise SetupError("tools")
    elif not paths:
        new_rustup = True
        _install_rustup(language, host)
        paths = _rust_paths_after_install()
    rustup = paths.get("rustup")
    cargo = paths["cargo"]
    build = [cargo]
    if new_rustup and rustup:
        build.append("+stable")
    build.extend([*BUILD_FLAGS, root / "native" / "Cargo.toml"])
    env = os.environ.copy()
    if system == "windows":
        vs_path = _windows_vs_path()
        if not vs_path:
            raise SetupError("compiler")
        env.update(_windows_build_environment(vs_path))
    rust_bins = list(dict.fromkeys(str(paths[name].parent)
                                   for name in ("cargo", "rustc")))
    env["PATH"] = os.pathsep.join([*rust_bins, env.get("PATH", "")])
    env["CARGO_TARGET_DIR"] = str(root / "native" / "target")
    _command(language, build, cwd=root, env=env, timeout=1800)
    suffix = ".exe" if system == "windows" else ""
    binary = root / "native" / "target" / "release" / f"chzzk-native{suffix}"
    if not binary.is_file():
        raise SetupError("build")
    _probe_binary(binary)
    _publish_binary(binary, root / "native")
    return True


def configure_rust(language, *, root=BASE_DIR):
    """Offer Rust support and return whether a verified helper is available."""
    root = Path(root)
    native_dir = root / "native"
    disabled = native_dir / ".disabled"
    _say(language, "intro")
    try:
        while True:
            choice = input(translate(language, "rust_install.prompt")).strip() or "2"
            if choice in {"1", "2"}:
                break
        if choice == "2":
            disabled.parent.mkdir(parents=True, exist_ok=True)
            disabled.touch()
            _say(language, "disabled")
            return False
        _say(language, "installing")
        if not _enable(language, root):
            disabled.parent.mkdir(parents=True, exist_ok=True)
            disabled.touch()
            return False
        disabled.unlink(missing_ok=True)
        _say(language, "ready")
        return True
    except KeyboardInterrupt:
        disabled.parent.mkdir(parents=True, exist_ok=True)
        disabled.touch()
        raise
    except SetupError as error:
        disabled.parent.mkdir(parents=True, exist_ok=True)
        disabled.touch()
        _say(language, "failed", error=translate(
            language, f"rust_install.error_{error.code}"
        ))
        _say(language, "manual", url=RUST_INSTALL_URL, command=MANUAL_BUILD)
        return False
    except (EOFError, OSError, urllib.error.URLError,
            subprocess.SubprocessError) as error:
        disabled.parent.mkdir(parents=True, exist_ok=True)
        disabled.touch()
        _say(language, "failed", error=error)
        _say(language, "manual", url=RUST_INSTALL_URL, command=MANUAL_BUILD)
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=translate(DEFAULT_LANGUAGE, "rust_install.intro")
    )
    parser.add_argument(
        "--language", choices=tuple(SUPPORTED_LANGUAGES), default=DEFAULT_LANGUAGE,
        help=translate(DEFAULT_LANGUAGE, "rust_install.prompt"),
    )
    args = parser.parse_args(argv)
    return 0 if configure_rust(args.language) else 1


if __name__ == "__main__":
    raise SystemExit(main())
