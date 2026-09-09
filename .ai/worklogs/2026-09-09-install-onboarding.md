# 설치 방식 선택과 첫 실행 안내 개선

## 요청과 확인

- 2026-09-09: GUI에서 CLI 쿠키 로그인 직접 실행, 최초 언어/채널 마법사, 긴 파일명으로 제목이 잘린 경우만 TXT, Noto CJK 폴더로 폰트 경로 고정 및 불필요 폰트 삭제, CLI 메뉴 정리, 쉬운 종료 명칭, 설치 중 GUI/CLI 선택, Windows GUI 콘솔 숨김, Windows 설정 저장 WinError 5 수정.
- 시작 브랜치 `gui`, HEAD `f194e71`. 구현 완료 후 사용자가 2026-09-09에 커밋과 푸시를 명시적으로 요청했다.
- `config_store.load_config()`가 읽기 핸들을 닫기 전에 정규화 결과를 `os.replace()`로 저장하고 있었다. Windows에서 자기 읽기 핸들이 교체를 막는 경로를 없애도록 읽기 블록을 먼저 종료했다. 외부 잠금/권한 오류일 때 원본을 보존하는 규칙은 유지한다.

## 구현 완료

- `settings.py:collect_cli_cookies()`를 기존 CLI와 GUI 로그인에서 공유한다. `console_login.py`가 실제 터미널에서 `settings.py --browser-login`을 실행하고, 브라우저 로그인 후 Enter로 쿠키를 수집한다. 결과는 GUI 편집 화면으로 전달하며 저장 버튼을 누르기 전 설정 파일은 변경하지 않는다. 취소/창 닫힘/드라이버 오류를 구분하고 임시 인증 결과를 정리한다.
- 입력 대기 데몬에서 buffered stdin을 읽으면 취소 후 인터프리터 종료 시 `_enter_buffered_busy` 오류가 발생하는 것을 검증 중 발견했다. CLI와 중계 프로세스의 대기를 `os.read()`로 바꿨고 실제 자식 프로세스 취소/종료로 재검증했다. 터미널 시작 PID 표시는 임시 파일 교체로 완성된 값만 읽게 했다.
- `gui/setup_wizard.py`와 첫 실행 진입을 추가했다. 언어, 채널 검색/추가/편집/저장 위치, 완료 안내를 제공한다. 기존 설정을 초안으로 열고 완료할 때만 `onboarding_completed=true`와 함께 저장한다. 채널은 명시적으로 나중에 추가할 수 있으며 도움말 → 처음 설정에서 다시 연다.
- `scripts/finish_install.py`를 양쪽 설치 스크립트에 연결했다. GUI 선택 시에만 Qt 의존성을 설치하고 GUI를 실행하며, CLI 선택은 기존 설정으로 이어진다. `scripts/select_language.py`도 ConfigStore를 사용하고 최신 설정의 언어만 갱신하도록 통합했다.
- Windows GUI 실행은 `chzzk_gui.vbs` → 숨긴 uv → `--gui-script`의 pythonw 경로다. `.bat`도 VBS로 연결한다. GUI 녹화 프로세스는 콘솔 Python을 사용해 JSON 통신을 유지하고, FFmpeg 인코더 probe/녹화 자식의 추가 창도 숨긴다. CLI 로그인 창은 의도적으로 표시한다.
- `settings.py`의 최상위 메뉴를 채널/녹화·화질/인코딩/NAVER 로그인/네트워크/언어·로그로 정리했다. 하위 메뉴는 0번 뒤로, 최상위는 0번 종료이며 코덱 3종 편집 순서를 통일했다. 채널 삭제 시 다른 채널의 identifier/지연도 보존한다.
- `chzzk_record.py`에서 실제 생성 파일명과 원래 기본 이름을 비교해 축약된 제목에만 원본 TXT를 저장한다. 짧은 제목, 분할 녹화, 부분 결과 보존 및 기존 해시 파일명 규칙을 유지한다.
- `gui/appearance.py` 폰트 경로를 지정 CJK 묶음의 `Variable/TTF/Subset/NotoSansKR-VF.ttf`로 고정했다. 사용자 요청에 따라 불필요한 폰트 16개와 빈 하위 폴더를 삭제했고, 약 10.4MB 한국어 가변 폰트와 LICENSE만 남겼다. 삭제한 폰트는 미추적 파일이었으므로 git diff의 삭제 목록에는 나타나지 않는다.
- UI의 '안전 종료' 등을 '종료', '녹화 중지'로 바꿨으며 녹화 정리 대기 동작은 유지했다. `i18n.py`의 5개 언어 및 5개 README를 함께 갱신했다.

## 검증 결과

검증 코드는 Git에서 제외된 `.gui-validation/`에만 두었다. 실제 설정/쿠키/개인 녹화 파일은 사용하거나 수정하지 않았다.

- `onboarding_check.py`: Windows에서 읽기 핸들이 열려 있으면 교체를 거부하는 조건을 모사해 언어 전용 설정의 정규화 저장 성공 확인. 외부 PermissionError에는 기존 파일 보존. CLI 전체 메뉴 왕복, 코덱 상호 배타, 화질, 5개 언어 마법사, 취소/완료 저장, 검색 결과 추가 통과.
- `install_login_check.py`: 설치 GUI/CLI 분기와 GUI에만 Qt 설치, 플랫폼별 터미널 인자 및 한글/공백 경로, pythonw의 콘솔 Python 선택, Windows 창 숨김 플래그, 공용 CLI 확인/취소, 결과 파일 권한 및 정리 통과. 실제 자식 프로세스의 합성 쿠키 전달, stdin이 열린 상태에서 취소 후 정상 종료, 설치 언어 저장 시 다른 변경 보존도 통과. 실제 Windows 실행을 대신한 모사 검증이다.
- `encoding_check.py --title-only`: 실제 FFmpeg와 녹화 함수로 짧은 제목 단일 1개/분할 4개에서 TXT 없음, 긴 제목 단일 1개/분할 4개에서 정확한 원본 TXT 확인. 한글/이모지/개행/리터럴 `%03d`를 포함한 제목과 256×144 30fps 합성 영상을 사용했다. 결과 위치 `.gui-validation/encoding-waw_0n1a`, 로그 `title-condition-check.log`.
- `process_options_check.py`: 실제 녹화 프로세스 JSON 중지/부모 EOF, 스트림 화질 조회, GUI 로그인 출력/오류/시작 중 취소, 트레이 종료 시 로그인 정리 대기 통과. Linux 런타임과 같은 uvloop 경로로 확인했다.
- `enhancements_check.py`: 화질/채널 상속, 실제 인코더 probe(CPU H.264 동작 포함), 쿠키 수집 모형, CLI 화질/H.264/채널 설정, Qt 5개 언어/폰트/제목 열/우클릭/트레이 회귀 검증 통과.
- 두 채널 중 첫 채널을 CLI에서 삭제한 뒤 남은 채널의 identifier와 사용자 지연(31초)이 그대로 저장되는 추가 검증 통과.
- 첫 실행 마법사 3개 화면을 실제 MainWindow 스타일을 상속한 offscreen Qt로 캡처하고 시각 점검했다. 기록용 [언어 선택](../assets/qt-gui-setup-language.png), [채널 추가](../assets/qt-gui-setup-channels.png)는 합성 채널 화면이다.
- 변경 Python의 `compileall`/`py_compile`, Ruff E9/F 검사, GUI·신규 공용 파일 및 CLI의 import/format 검사(16개 파일), `bash -n install chzzk_gui settings`, `git diff --check`, 변경 `.ai` 문서의 로컬 링크 존재 검증 통과.

## 근거와 미검증 사항

- uv의 [스크립트 실행 문서](https://docs.astral.sh/uv/guides/scripts/) 및 [CLI 옵션 문서](https://docs.astral.sh/uv/reference/cli/)에서 Windows pythonw/`--gui-script` 동작을 확인했다. [Qt 6.11 공식 QProcess 소스](https://raw.githubusercontent.com/qt/qtbase/6.11/src/corelib/io/qprocess_win.cpp)의 부모 콘솔 부재 시 `CREATE_NO_WINDOW` 적용 경로도 확인했다.
- 실제 Windows/macOS 설치와 창 표시 여부, 개인 NAVER 계정의 브라우저 로그인은 이 Linux 환경에서 실행하지 못했다. 실제 CHZZK 장시간 녹화와 하드웨어 인코더 동작도 이번 검증에 포함하지 않았다.
- 2026-09-09 로컬 구현과 위 검증을 완료했다. 개인 녹화 폴더 `아리사/`는 건드리지 않았다.

## 커밋·푸시 요청

- 사용자 요청에 따라 `gui` 브랜치의 관련 코드, 5개 언어 README, `.ai` 문서 및 합성 마법사 화면만 커밋한다. 개인 녹화 폴더와 무시된 검증 산출물은 제외한다.
- 커밋 전 현재 브랜치/변경 목록과 `git diff --check`를 다시 확인했다. 구현 검증 후 코드가 바뀌지 않아 동일한 기능 검증을 반복하지 않는다.
- author와 committer는 이전 GUI 커밋의 관례에 맞춰 `Codex <codex@openai.com>`을 사용한다. 푸시 후 `git ls-remote`로 원격 브랜치와 로컬 HEAD 일치를 확인한다.
