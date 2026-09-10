# 프로젝트 작업 지식

최종 확인: 2026-09-10. 아래 구조는 확인 당시의 코드 기준이며, 작업 전에 현재 코드와 git 상태를 다시 확인한다.

## 지침과 메모 위치

- 작업 지침: [AGENTS.md](AGENTS.md), [codex.md](codex.md).
- 루트 `AGENTS.md`는 `.ai/` 지침과 이 파일을 읽도록 안내하는 진입 파일이다.
- 사용자는 매 작업마다 `.ai/`에 후속 작업을 위한 메모를 남기도록 요청했다. 세부 기록은 `worklogs/`, 제안 단계 설계는 `plans/`에 저장한다.

## 현재 코드 구조

- `chzzk_record.py`: `asyncio` 기반 녹화 관리, Streamlink/FFmpeg 자식 프로세스 실행, 인코더 probe/fallback, Rich 진행 화면을 포함한다. `manage_recording_tasks()`, `record_stream()`, `display_progress()`, `main()`이 주요 연결 지점이다.
- `chzzk_record.py`의 uvloop 설정, 로거 생성, DNS 설치는 `run()`/`main()`에서 수행한다. import 시 파일/UI 부수 효과를 없앴다. CLI 실행은 그대로이며 GUI는 `--gui-events --config` 인자를 사용한다.
- `settings.py`: `main()` 실행 가드가 있는 CLI다. 채널/녹화·화질/인코딩/NAVER 로그인/네트워크/언어·로그의 6개 메뉴, 0번 뒤로/종료로 구성한다. `config_store.py`의 공용 설정, `channel_service.py`의 채널 검색, `browser_login.py`의 쿠키 수집을 사용한다.
- GUI 로그인은 `console_login.py`가 별도 터미널에 `settings.py --browser-login`을 열어 CLI와 동일한 `collect_cli_cookies()`를 실행한다. 로그인 후 Enter를 누르면 쿠키가 GUI 편집 화면으로 돌아오고 사용자가 저장할 때 설정에 반영한다. 취소 신호와 결과는 임시 디렉터리/GUI 파이프로 전달하며 쿠키 값을 로그에 출력하지 않는다. 취소 대기 스레드는 종료 시 buffered stdin 잠금을 피하도록 `os.read()`를 사용한다.
- `browser_login.py`는 브라우저 capabilities로 Chromium 전용 CDP 호출을 제한한다. Firefox에도 같은 이름의 메서드가 노출될 수 있으므로 메서드 존재만으로 CDP 지원을 판단하지 않는다. 로그인 성공 시점의 쿠키를 보존하고 열린 NAVER 탭/HttpOnly 쿠키를 수집한다.
- `config.json`: CLI와 실제 Qt GUI가 공유한다. 실제 인증 정보는 기록하지 않는다.
- `config_store.py:ConfigStore`: 파일 잠금과 revision 비교로 편집 충돌을 감지한다. 정규화 결과를 저장하기 전에 기존 파일의 읽기 핸들을 닫는다(Windows 자체 파일 교체의 WinError 5 방지). 임시 파일 교체를 반복해도 실패하면 직접 덮어쓰지 않고 마지막 정상 파일을 보존한다. 손상 설정 백업에 실패하면 원본을 덮어쓰지 않는다. 설치 언어 저장도 이 경로를 사용하며 언어만 최신 설정에 반영한다.
- `chzzk_gui.py`/`gui/`: PySide6 리본 창, 전체 설정, 채널 관리, 5개 언어, 도움말, 프로필 이미지 및 녹화 프레임 미리보기. `uv run --extra gui chzzk_gui.py`로 실행한다. CLI는 Qt 의존성이 필요 없다.
- `install`/`install.bat`는 언어 및 기본 설치 후 `scripts/finish_install.py`에서 GUI/CLI를 선택한다. CLI는 기존 설정 메뉴를 열고, GUI는 Qt 선택 의존성을 설치한 뒤 바로 실행한다. Windows는 `chzzk_gui.vbs`가 숨긴 uv 실행과 `--gui-script`의 pythonw를 사용하며, `.bat`도 VBS로 연결한다. `process_utils.py`는 콘솔 Python 선택 및 Windows 자식 콘솔 숨김을 공용화한다. 로그인 터미널만 의도적으로 표시한다.
- `gui/setup_wizard.py`는 첫 GUI 실행에 언어 → 채널 추가/저장 위치 → 완료를 안내한다. `gui_settings.onboarding_completed` 기본값은 false이며 완료할 때만 초안과 true를 함께 저장한다. 취소하면 기존 설정을 유지하고 다음 실행에 다시 안내한다. 채널 없이 진행하려면 나중에 추가를 명시적으로 선택한다. 도움말 → 처음 설정에서 다시 열 수 있다.
- `recording_options.py`: 전역 및 채널 화질, 채널별 분할 상속/끄기, 실제 제공 스트림 선택 및 크기/FPS 변환 규칙. `encoding_h264.py`는 6종 H.264 인수와 실제 probe를 담당한다. H.264/HEVC/AV1은 하나만 활성화한다.
- `channels[].recording_split_minutes`와 `channels[].quality_settings`는 없거나 null이면 전체 설정을 상속한다. 채널 분할 0은 전역 설정과 무관하게 분할을 끈다.
- `gui_settings.close_to_tray` 기본값은 true다. 트레이가 있을 때 창 닫기는 백그라운드 유지, 트레이 메뉴의 종료는 기존 녹화 정리를 기다린다. 트레이가 없으면 창 닫기로 종료한다. 사용자 명칭은 '녹화 중지', '종료'로 통일했으며 파일 정리 동작은 유지한다.
- `gui/appearance.py`는 `font/02_NotoSansCJK-TTF-VF/Variable/OTC/NotoSansCJK-VF.ttf.ttc`에서 5개 CJK family를 등록하고 언어별 KR/JP/SC/TC 우선순위와 wght=400을 설정한다. 기존 KR 서브셋 대신 제공된 TTC와 LICENSE를 배포한다. Windows는 DirectWrite/모니터별 DPI와 point 단위 폰트를 사용한다.
- `chzzk_record.py:recording_output_size()`는 분할 녹화의 실제 파일 크기를 합산한다. FFmpeg segment muxer의 `total_size=N/A`를 0으로 취급하지 않으며 GUI/CLI의 용량·속도·비트레이트와 JSON `total_bytes`에 사용한다.
- Linux는 폴더의 `Chzzk-Rekoda.desktop` 클릭으로 실행할 수 있다. `%k`로 파일 위치를 받으므로 폴더 이동/한글/공백 경로를 지원한다. `chzzk_gui`는 설치된 Qt Python과 사용자 uv 경로를 찾는다. 파일 관리자별 실행 허용 정책은 별도다.
- 설정 리본의 '프로그램 완전 종료'는 `quit_application()`으로 녹화 정리를 기다리고 트레이까지 종료한다. CLI 화면은 별도 터미널 화면에서 변경된 내용만 1초 간격으로 갱신하며, Windows VT 콘솔 모드를 작업 종료 시 복원한다.
- `chzzk_record.py:save_original_title()`은 파일명 길이 제한으로 제목을 축약한 녹화에만 호출한다. 일반/분할/유효한 부분 녹화 파일 옆에 원본 제목 TXT를 저장하고 기존 축약·해시는 유지한다. 정상 길이 제목에는 TXT를 새로 만들지 않는다.
- `recorder_bridge.py`: 버전 1 JSON 이벤트와 stop 명령/부모 stdin EOF 종료. Windows Qt의 `FILE_FLAG_OVERLAPPED` 파이프는 `process_utils.read_pipe()/write_pipe()`에서 `_winapi`의 overlapped 입출력과 완료 대기로 처리한다. 일반 CRT stdin/stdout으로 되돌리지 않는다. 다른 OS는 `os.read()/os.write()`를 사용한다. stdout 기록은 크기가 제한된 큐를 통해 보내 녹화 파이프를 막지 않는다. 종료 전 사용자 중지/앱 종료/제어 EOF/읽기·쓰기 실패/잘못된 응답을 구분해 이유와 오류 번호를 기록하며 녹화 정리는 기존 경로를 유지한다.
- `process_lock.py`: 동일 프로젝트의 CLI/GUI 중복 녹화를 막는 OS 소유 잠금이다. 강제 종료 후 남은 잠금 파일 자체는 실행 중이라는 뜻이 아니다.
- `gui/services.py:Preview`: 현재 녹화 파일에서 음성 없이 프레임을 5초마다 갱신한다. 출력 버퍼를 고려해 진행 시간 기준 약 8초 이전 위치를 읽는다. 분할 파일이 아직 비어 있으면 최근 읽을 수 있는 파일을 사용한다. 미리보기를 꺼도 녹화는 계속한다.
- `chzzk_record.py:load_config_async()`는 설정 읽기 실패 시 마지막 유효 설정을 유지한다. 설정 저장 도중 활성 녹화가 취소되지 않도록 이 동작을 보존한다.
- `chzzk_record.py:main()`은 종료 시 녹화 정리와 마지막 로그 표시를 처리한다. GUI의 중지/종료도 이 정리 경로를 거쳐야 한다.
- 사용자에게 보이는 문구는 `i18n.py`의 5개 언어를 함께 관리한다. `pyproject.toml`은 Python 3.12 이상이며 PySide6는 `gui` 선택 의존성이다. `uv.lock`은 Qt 6.11.2를 포함한다.
- 저장 폴더 열기의 번역 키는 `gui.folder`다. 리본과 채널 우클릭 메뉴에서 같은 키를 사용하며, 존재하지 않는 `gui.open_folder`를 사용하면 키 원문이 화면에 표시된다.
- GUI 리본은 `QTabWidget` 안의 한 줄 `QToolBar`이며, 좁은 창에서 넘치는 `QAction`은 Qt 더보기 메뉴로 이동한다. 시작/중지 활성 상태는 버튼 위젯 대신 QAction에 적용해 더보기에서도 일치시킨다. `gui/theme.py`는 밝은/어두운 공용 스타일, `gui/icons.py`는 선형 명령 아이콘을 관리한다. `gui/common.py:ElidedLabel`은 미리보기 제목을 한 줄로 줄이고 전체 제목을 이스케이프한 툴팁으로 보존한다. 디자인/배율 검증은 [리본 디자인 정리](worklogs/2026-09-10-compact-gui-design.md)를 참고한다.
- 앱 아이콘은 사용자 제공 이미지를 변환한 `assets/chzzk-rekoda.png`(512px)와 `.ico`(16~256px 10개 크기)를 공용으로 사용한다. 민트색 아이콘 바깥의 검은 모서리는 실제 알파 투명도로 제거했으며, PNG와 ICO의 모든 크기에서 투명도를 유지한다. `gui/appearance.py:application_icon()`은 창/트레이/앱 아이콘을 반환한다. `gui/desktop.py`는 Windows AppUserModelID를 UI 생성 전에 지정하고, Linux는 XDG 사용자 아이콘 테마와 앱 목록의 `.desktop`을 등록한다. `chzzk_gui.vbs`는 설치 폴더에 ICO를 지정한 `Chzzk Rekoda.lnk`를 생성/갱신한다. 바로가기에는 로컬 경로가 들어가므로 Git에서 제외한다. 세부 검증은 [앱 아이콘 적용 기록](worklogs/2026-09-10-app-icon.md)을 참고한다.

## 현재 논의와 관련 기록

- 사용자 확정 요구사항(2026-09-07): 깔끔하고 누구나 사용할 수 있는 리본 UI, 설정 위에 잠시 포인터를 두면 표시되는 설명, CLI와 GUI를 모두 사용할 수 있는 구조.
- PySide6 + Qt Widgets, 별도 녹화 프로세스, 도움말 700ms 지연을 실제 구현에 사용했다. 사용자가 구체적인 지연 수치를 지정한 것은 아니다.
- 초기에는 사용자가 `리본 시안의 모든 설정 완성`을 선택했고, 이후 실제 구현과 채널 아이콘/현재 녹화 영상 미리보기를 명시적으로 요청했다. 실제 GUI 연결 단계로 범위가 확대되어 구현했다.
- Linux offscreen Qt, 공개 채널 API/프로필 이미지, 합성 TS/MKV/WebM/분할 파일 프레임과 파일 정리를 검증했다. NAVER 로그인은 2026-09-09 사용자가 정상 작동을 확인했다. 에이전트의 실제 계정 로그인, Windows/macOS, 실제 장시간 CHZZK 녹화 및 하드웨어 인코더는 미검증이다.
- 2026-09-10 Windows GUI 녹화 중단의 전체 로그는 종료 신호 후 FFmpeg 빈 입력 오류가 발생하는 순서였다. Qt 파이프 입출력 호환성을 수정하고 종료 원인 진단을 추가한 뒤 사용자가 "녹화 잘 되네"라고 정상 녹화를 확인했다. Linux 실제 Qt→Streamlink→FFmpeg 파이프와 Windows API 모사 검증도 통과했다. Windows 정상 녹화는 사용자 확인 결과이며 에이전트의 직접 실행 검증과 구분한다. High DPI 글자와 CMD 점멸의 Windows 실환경 확인은 별도로 남아 있다.
- [Qt GUI 설계](plans/qt-gui.md)
- [GUI 설정 대응표](plans/gui-settings-coverage.md)
- [지침 정리, 작업 메모 규칙 및 GUI 구조 검토](worklogs/2026-09-06-ai-notes-qt-gui.md)
- [리본 UI와 도움말 요구사항 반영](worklogs/2026-09-07-ribbon-ui.md)
- [전체 설정 시안 구현과 검증](worklogs/2026-09-07-all-settings-preview.md)
- [실제 Qt GUI, 프로필 이미지와 녹화 미리보기 구현](worklogs/2026-09-08-qt-gui-implementation.md)
- [쿠키 개선, 채널별 분할·화질, H.264, 트레이와 제목 TXT](worklogs/2026-09-08-gui-recording-options.md)
- [설치 방식 선택, 첫 실행 마법사, CLI 로그인 연결과 Windows 저장 수정](worklogs/2026-09-09-install-onboarding.md)
- [분할 용량, 다국어 TTC, DPI와 플랫폼 실행 개선](worklogs/2026-09-10-gui-platform-fixes.md)
