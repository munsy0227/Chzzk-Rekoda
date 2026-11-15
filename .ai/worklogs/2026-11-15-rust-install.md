# 선택형 Rust 최초 설치 및 자동 도구 설치

- 확인일: 2026-11-15 (Asia/Seoul).
- 요청: 최초 설치에서 Rust 기능 사용 여부를 묻고, Windows/macOS/Ubuntu/Debian/Fedora/Arch Linux에서는 필요한 Rust를 자동 설치하며 다른 환경은 수동 안내.
- 기존 `codex/rust-features`에서 진행했다. 작업 시작 시 2차 검증 제안의 `.ai/KNOWLEDGE.md`, Rust 기능 worklog, `plans/rust-secondary-validation.md`만 미커밋 상태였으며 해당 검토 내용을 보존했다. 이번 작업은 2차 미디어 검증기의 제품 구현을 포함하지 않는다.

## 변경

- `scripts/finish_install.py`: 두 OS 설치 진입점이 공유하는 기존 함수에서 언어를 읽은 뒤, GUI/CLI 선택 전에 Rust 선택을 호출한다. 기존 GUI 의존성 실패의 종료 정책은 유지한다.
- `scripts/install_rust.py`: `configure_rust(language, root=...)`에서 1=Rust, 2=Python(기본)을 선택한다. 표준 라이브러리만 사용하고 root 설정/쿠키를 읽지 않는다. x86_64/aarch64의 Windows·macOS 및 정확히 Ubuntu/Debian/Fedora/Arch/ArchLinux ID만 자동 처리하며 다른 OS·아키텍처에는 공식 Rust 설치 링크와 수동 빌드/배치/활성화 안내를 제공한다.
- Linux: 사용자의 추가 지시에 따라 Rust 자체도 공식 패키지 관리자를 사용한다. Ubuntu/Debian은 `rustc cargo`, Fedora는 `rust cargo`, Arch는 Cargo를 포함하는 `rust` 패키지다. 필요한 C/C++·pkg-config·OpenSSL 개발 파일·CA 패키지도 apt-get/dnf/pacman으로 설치한다. 권한이 필요하면 sudo를 사용하고 전체 OS 업그레이드나 외부 저장소 추가는 하지 않는다. 배포판은 `platform.freedesktop_os_release()`로 판별한다. 공식 패키지 버전이 오래되어 빌드에 실패하면 자동으로 외부 Rustup 설치로 우회하지 않고 수동 안내와 Python 대체를 유지한다.
- macOS: 기존 Xcode/Command Line Tools·clang을 확인하고 필요 시 `xcode-select --install`을 호출한다. 사용자가 OS 설치 창에서 완료한 뒤 확인하도록 하며 전체 시스템 업데이트는 하지 않는다.
- Windows: vswhere·MSVC·Windows SDK를 확인한다. 새 Build Tools는 winget을 사용하고, 부재/불완전 설치는 공식 서명된 v17 bootstrapper로 설치 또는 해당 VS 2022 Build Tools 인스턴스만 modify한다. v18 인스턴스는 수정하지 않는다. ARM64 도구도 구분한다. UAC 거절 후 별도 설치기를 재시도하지 않고, 자동 재부팅하지 않는다. Microsoft 인증서 서명 검사는 임시 PowerShell 파일의 명시적 인자로 경로를 전달하고 유효 서명·정확한 Microsoft Corporation 게시자를 확인한다.
- Rust/Cargo가 사용 가능하면 기존 도구를 재사용한다. Windows/macOS에서 없거나 초기화되지 않았으면 공식 Rustup host별 파일과 SHA-256을 받아 확인한 뒤 사용자 계정에 minimal/stable을 설치한다. Linux는 공식 패키지 설치 뒤 시스템 도구 경로를 우선 확인한다. 셸 초기화 파일을 source하지 않고 빌드 자식 PATH에 도구 경로를 넣는다. 출력 target 경로도 명시해 외부 `CARGO_TARGET_DIR`의 영향을 분리한다.
- 빌드 성공 후 `serve` hello 검증을 통과한 실행 파일만 `native/bin`에 원자적으로 배치한다. 일반 설치 실패 시 기존 바이너리를 덮어쓰지 않고 수동 안내와 함께 Python 설치로 진행한다. 선택 저장 자체가 실패하면 성공했다고 표시하지 않는다.
- `native_backend.py`, `.gitignore`: `native/.disabled`는 실행 파일 검색보다 우선한다. 거절/실패 시 live/report 모두 Rust를 사용하지 않고, 성공 후 표식을 제거한다. `native/bin`과 표식은 Git에서 제외한다. 개인 녹화 설정 형식은 변경하지 않았다.
- `i18n.py` 5개 언어 설치 문구/오류, 5개 README·CHANGELOG와 `native/README.md`를 갱신했다. 수동 빌드는 새 실행 파일을 `native/bin`에 배치한 뒤 표식을 제거하도록 안내해 이전 바이너리 우선 검색 문제를 피한다.
- 회귀 CI의 Windows·macOS 작업에 설치 테스트를 추가했다. CI 전용 테스트는 기존 MSVC 환경과 Microsoft 서명 검사(공백·한글·따옴표 경로), macOS의 기존 CLT 탐지만 수행하며 OS 설치를 실행하지 않는다.

## 검증

- 최종 설치 집중 검사 29개: 실패/오류 0, CI 호스트 전용 2개는 로컬에서 skip. 모의 설치 24개, GUI/CLI 마무리 3개, CI 호스트 확인 2개로 구성한다. Linux Rust 자체의 공식 패키지 설치, 패키지 설치 후 시스템 Cargo 우선 사용, 실패 시 Rustup 미호출 및 macOS Rustup 유지도 확인했다. 다운로드·패키지 설치·OS 변경은 테스트에서 모두 모의 처리했다.
- 최종 전체 unittest: 199개, 74.638초, 실패/오류 0, CI 호스트 전용 2개 skip. 거절 시 기존 실행 파일이 있어도 live/report를 호출하지 않는 회귀 검사를 포함한다. 로그: `.cache/rust-install-tests.log`, `rust-install-full-tests.log`.
- 실제 Linux 빌드 smoke: 기존 `/tmp`의 Rust 1.100.0을 사용해 임시 프로젝트에서 Cargo release 빌드, hello 검증, `native/bin` 배치, 배치된 실행 파일 재검증, Python 선택 후 검색 비활성화를 확인했다. Linux 패키지 정책 수정 뒤 재실행도 통과(14.23초 빌드). 시스템 prerequisite 함수는 모의 처리하고 Rustup 설치 호출은 금지했다. 실제 OS 패키지/새 SDK 설치는 하지 않았다. 바이너리 4,480,848 bytes. 자료: `.cache/rust-installer-build-smoke.log`, `rust-installer-smoke-result.json`.
- 새 Python 설치기·테스트와 native 연결 파일 Ruff, 수정 Python 문법 컴파일, workflow YAML, `git diff --check` 통과.
- 게시 후 CI의 실제 호스트 확인 결과는 해당 Actions run과 최종 응답에서 구분한다. 빈 OS에 새 Rust/컴파일러/SDK를 설치하는 관리자 승인·패키지 관리자·UAC·CLT 전체 실설치는 미검증이며, 이번 개발 환경의 시스템에는 설치 명령을 실행하지 않았다.

## 공식 확인 자료

- [Rust 설치](https://rust-lang.org/tools/install/), [Rustup 기타 설치·host별 체크섬](https://rust-lang.github.io/rustup/installation/other.html), [Windows MSVC](https://rust-lang.github.io/rustup/installation/windows.html).
- [Microsoft Visual Studio 명령줄 설치](https://learn.microsoft.com/en-us/visualstudio/install/use-command-line-parameters-to-install-visual-studio?view=vs-2022), [PowerShell 인자 규칙](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_powershell_exe?view=powershell-5.1).
- 배포판 공식 패키지: [Ubuntu Cargo](https://packages.ubuntu.com/cargo), [Debian Cargo](https://packages.debian.org/trixie/cargo), [Fedora Rust 설치](https://developer.fedoraproject.org/tech/languages/rust/rust-installation.html), [Arch Rust](https://archlinux.org/packages/extra/x86_64/rust/). 조사 시 Debian/일부 Ubuntu 기본 컴파일러는 최신 잠금 의존성 요구보다 오래된 경우가 있어 자동 빌드 성공으로 일반화하지 않는다.
