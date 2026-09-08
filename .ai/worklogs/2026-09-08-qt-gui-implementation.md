# Qt GUI, 채널 프로필 이미지, 녹화 미리보기 구현

## 요청과 범위

- 2026-09-07 사용자가 리본 시안을 실제 구현하고, 조회 가능한 채널 아이콘과 현재 녹화 영상 미리보기를 추가해 달라고 요청했다. 2026-09-08 같은 작업을 이어 구현과 아래 검증을 완료했다.
- CLI와 GUI 모두 유지하며 기존 설정 전체를 제공한다. 구현 단계에서는 원격 push/커밋을 요청하지 않았고, 이후 사용자가 `gui` 브랜치 생성과 로컬 커밋을 요청했다.

## 구현한 구조

- `chzzk_gui.py`, `chzzk_gui`, `chzzk_gui.bat`: 선택 의존성 `gui`를 사용하는 PySide6 진입점. `uv run --extra gui chzzk_gui.py`로 실행한다.
- `gui/window.py`: 홈/채널/설정/도움말 리본, 채널 목록, 상태/로그, 녹화 시작·안전 종료, 프로필 아이콘과 현재 파일 프레임 미리보기.
- `gui/settings_dialog.py`: 전체 설정의 저장·취소, HEVC/AV1 상호 배타, 모든 인코더/프리셋, 입력 검증, 로그인/쿠키, 네트워크, 5개 언어/로그, 채널 경로/지연/활성화.
- `gui/common.py`: 700ms 기본 툴팁, 키보드 포커스 설명, F1과 설명 버튼.
- `config_store.py`: 기존 기본값·정규화·마이그레이션·손상 파일 백업을 분리했다. CLI/GUI가 같은 `ConfigStore`를 사용하며 편집 충돌은 SHA-256 revision과 파일 잠금으로 거부한다. 임시 파일 교체가 계속 실패하면 직접 덮어쓰던 경로를 제거하고 마지막 정상 파일을 보존한다.
- `settings.py`: 기존 메뉴를 `main()` 실행 가드로 옮겼다. import만으로 메뉴/파일 I/O를 수행하지 않는다.
- `channel_service.py`: 기존 채널 검색/조회에 CHZZK 응답의 `channelImageUrl`을 포함한다. 공개 HTTPS 이미지의 허용된 NAVER CDN 주소만 사용한다. 이미지 다운로드/크기 제한과 이름 아이콘 fallback은 `gui/services.py`가 담당한다.
- `browser_login.py`: CLI와 GUI가 공용 브라우저 쿠키 수집 함수를 사용한다. GUI는 별도 프로세스에서 새 브라우저를 열어 최대 3분 동안 로그인 쿠키를 확인한다. 쿠키는 private stdout 파이프로만 전달하며 GUI 로그에 출력하지 않는다.
- `chzzk_record.py`: import 부수 효과를 실행 시점으로 이동했다. `--gui-events --config` 모드와 현재 파일/분할 템플릿/방송 제목 상태를 추가했으며 인코딩 옵션과 파일 정리 로직은 복제하지 않았다.
- `recorder_bridge.py`: 버전 1 JSON 이벤트, 크기를 제한한 비동기 출력 큐, 명시적 stop 명령 및 부모 stdin EOF 시 기존 shutdown 경로를 사용한다.
- `process_lock.py`: OS 소유 잠금으로 동일 프로젝트의 CLI/GUI 중복 녹화를 방지한다.
- 미리보기는 음성 없는 정지 프레임을 5초마다 갱신한다. 별도 방송 URL을 재생하지 않고 현재 녹화 파일을 FFmpeg로 읽는다. 추출 프로세스는 7초/이미지 2MiB로 제한하며 채널 변경 시 이전 결과를 버린다.
- 출력 버퍼 때문에 최신 진행 시점의 프레임을 읽지 못하는 경우를 확인해 약 8초 이전 위치를 사용한다. 분할 파일이 막 만들어져 비어 있으면 현재 템플릿에서 최근 읽을 수 있는 세그먼트를 고르고 해당 파일 기준으로 시간을 계산한다.
- 설정 창을 열며 외부 변경을 읽은 뒤 취소하는 경우에도 메인 창 데이터를 함께 갱신한다. revision만 새 값으로 바뀌어 이후 저장이 오래된 데이터로 덮어쓰는 문제를 방지한다. 녹화 시작 전에도 최신 설정을 다시 읽는다.
- `i18n.py`: 추가 GUI 문구와 도움말의 5개 언어를 모두 추가했다. README 5개 언어에 GUI 실행 및 적용 시점 안내를 추가했다.
- `pyproject.toml`/`uv.lock`: PySide6는 `gui` 선택 의존성이며 lock에는 PySide6 6.11.2 관련 4개 패키지만 추가됐다.

## 현재 확인한 검증

- Python 문법 컴파일, 변경 Python 모듈의 Ruff E9/F 검사, 신규/분리 모듈의 I 검사 및 12개 파일 포맷 검사, `git diff --check` 통과.
- Qt offscreen 실제 창/설정 폼 생성. 설정 19개 입력과 분할 입력이 초기 설정값과 일치했다.
- 인코더 12종 전체 프리셋, 상호 배타, 잘못된 비트레이트/DoH 거부, 단위 정규화, 파일 저장, 채널 편집, 5개 언어 설정 창 생성 통과.
- 기존 설정 메뉴와 녹화 모듈의 import 시 입력 대기/로거 생성이 없음. CLI와 GUI 공용 설정의 편집 충돌 거부, 원자적 교체 실패 시 파일 보존, 알려지지 않은 필드 보존, 손상 파일 백업 성공/실패 경로 통과.
- 쿠키 없이 공개 CHZZK 채널(침착맨)을 실제 검색/ID 조회하고 `nng-phinf.pstatic.net` 프로필 이미지(162535 bytes)를 다운로드했다. 실제 Qt 네트워크 요청으로 아이콘 표시와 FFmpeg 미리보기 표시도 확인했다.
- 실제 녹화 프로세스의 JSON 이벤트, 중복 실행 잠금, stop 명령, 부모 stdin EOF 종료와 종료 이벤트 확인.
- 프로세스가 아직 시작 중일 때 창을 닫아도 시작 완료 직후 stop을 전달하고 안전 종료하는 경로 통과. 로그 10,000건을 넣어도 IPC 큐는 256건으로 제한되고 최신 로그를 유지했다.
- 합성 H.264 입력을 사용하는 실제 녹화 파이프에서 TS·MKV·WebM 및 분할 TS 녹화 중 프레임 추출, 안전 종료, 최종 파일 ffprobe 확인 통과. 실제 CHZZK 응답과 Streamlink 입력만 합성 입력으로 대체했다. 분할 테스트는 검증 시간을 줄이려고 간격을 2초로 주입했다.
- WebM 검증 초기에는 테스트의 기본 asyncio 루프에서 종료 지연을 관찰했다. Linux 실제 실행과 동일한 uvloop를 사용한 최종 WebM/분할 녹화 검증은 지연 없이 종료됐다. 결과를 Windows 또는 기본 asyncio 루프 검증으로 확대 해석하지 않는다. 재개 후 검증 근거: `.gui-validation/media_check.py`, `.gui-validation/media-check.log`.
- 외부 설정 변경 → 설정 창 열기/취소 → 채널 설정 저장 시 외부 변경을 보존하는 회귀 검증 통과. CLI 메뉴 입력을 통한 공용 저장, 가짜 브라우저 드라이버의 쿠키 수집 및 성공/오류 시 종료도 확인했다.
- 5개 언어 모두 최소 창 너비 900px에서 설정 리본이 창 경계를 넘지 않았다. 밝은/어두운 테마와 설정 화면을 렌더링해 확인하고 테마 팔레트 및 콤보박스 화살표를 보완했다.
- 최종 화면: [녹화 미리보기](../assets/qt-gui-recording.png), [전체 설정 중 HEVC 화면](../assets/qt-gui-settings.png). 미리보기 화면은 합성 영상이며 실제 방송을 녹화한 화면이 아니다.
- 작업 재개 시 `/tmp` 가상환경/자료가 초기화되어 검증 자료를 무시되는 `.gui-validation/`에 보관한다. 현재 저장소 `.venv`는 Python 3.12.13과 GUI 의존성을 갖추고 있다.

## 완료 상태와 미검증

- 요청한 실제 Qt GUI, 전체 설정, 채널 프로필 이미지 조회, 현재 녹화 파일 미리보기와 CLI 공존 구현을 완료했다. 후속 로컬 커밋 작업은 아래에 기록한다. 원격 반영은 요청하지 않았다.
- 실제 NAVER 브라우저 로그인, Windows/macOS, 실제 CHZZK 장시간 녹화 및 하드웨어 인코더 실행은 아직 검증하지 않았다.
- 작업 재개 시 확인된 기존 사용자 폴더 `아리사/`의 파일과 개인 설정은 테스트하거나 변경하지 않았다. 검증 설정에는 인증 정보를 넣지 않았다.

## 후속 요청: gui 브랜치와 로컬 커밋

- 2026-09-08 사용자가 `gui` 브랜치를 만들어 현재 작업을 커밋하도록 요청했다. `main`의 `f6e3e53865c4c65d9fc1cb644ea75c448bbc9546`에서 원격 추적 없이 `gui`를 생성했다.
- 지침 정리는 `19c776e` (`docs: centralize AI instructions under .ai`)로 먼저 커밋했다. GUI 구현, 공용 모듈, 의존성, 번역, README와 관련 `.ai` 기록/검증 화면은 후속 기능 커밋 단위로 묶는다.
- Git 작성자 설정이 비어 있어 최근 로컬 작업 커밋과 동일한 `Codex <codex@openai.com>`을 커밋 명령에만 지정했다. 전역/저장소 설정을 바꾸지 않았다.
- 커밋 준비 중 수정 Python 파일의 문법 컴파일과 `git diff --check`를 다시 통과했다. 기능 검증은 위 결과를 참조한다.
- 사용자 녹화 폴더 `아리사/`, 개인 설정, 무시되는 `.gui-validation/` 자료는 커밋 대상에서 제외한다. 원격 push와 PR 생성은 이번 요청 범위에 없다.

## 참고 근거

- Qt 공식 문서: [QProcess](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html), [QThreadPool](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThreadPool.html), [QNetworkAccessManager](https://doc.qt.io/qtforpython-6/PySide6/QtNetwork/QNetworkAccessManager.html), [QImageReader](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QImageReader.html).
