# 프로젝트 작업 지식

최종 확인: 2026-09-08. 아래 구조는 확인 당시의 코드 기준이며, 작업 전에 현재 코드와 git 상태를 다시 확인한다.

## 지침과 메모 위치

- 작업 지침: [AGENTS.md](AGENTS.md), [codex.md](codex.md).
- 루트 `AGENTS.md`는 `.ai/` 지침과 이 파일을 읽도록 안내하는 진입 파일이다.
- 사용자는 매 작업마다 `.ai/`에 후속 작업을 위한 메모를 남기도록 요청했다. 세부 기록은 `worklogs/`, 제안 단계 설계는 `plans/`에 저장한다.

## 현재 코드 구조

- `chzzk_record.py`: `asyncio` 기반 녹화 관리, Streamlink/FFmpeg 자식 프로세스 실행, 인코더 probe/fallback, Rich 진행 화면을 포함한다. `manage_recording_tasks()`, `record_stream()`, `display_progress()`, `main()`이 주요 연결 지점이다.
- `chzzk_record.py`의 uvloop 설정, 로거 생성, DNS 설치는 `run()`/`main()`에서 수행한다. import 시 파일/UI 부수 효과를 없앴다. CLI 실행은 그대로이며 GUI는 `--gui-events --config` 인자를 사용한다.
- `settings.py`: `main()` 실행 가드가 있는 CLI다. `config_store.py`의 공용 기본값/정규화/마이그레이션/저장을 사용하고, 채널 검색은 `channel_service.py`, 브라우저 쿠키 수집은 `browser_login.py`를 공유한다.
- `config.json`: CLI와 실제 Qt GUI가 공유한다. 실제 인증 정보는 기록하지 않는다.
- `config_store.py:ConfigStore`: 파일 잠금과 revision 비교로 편집 충돌을 감지한다. 임시 파일 교체를 반복해도 실패하면 직접 덮어쓰지 않고 마지막 정상 파일을 보존한다. 손상 설정 백업에 실패하면 원본을 덮어쓰지 않는다.
- `chzzk_gui.py`/`gui/`: PySide6 리본 창, 전체 설정, 채널 관리, 5개 언어, 도움말, 프로필 이미지 및 녹화 프레임 미리보기. `uv run --extra gui chzzk_gui.py`로 실행한다. CLI는 Qt 의존성이 필요 없다.
- `recorder_bridge.py`: 버전 1 JSON 이벤트와 stop 명령/부모 stdin EOF 종료. 별도 녹화 프로세스가 기존 안전 종료를 수행한다. stdout 기록은 크기가 제한된 큐를 통해 보내 녹화 파이프를 막지 않는다.
- `process_lock.py`: 동일 프로젝트의 CLI/GUI 중복 녹화를 막는 OS 소유 잠금이다. 강제 종료 후 남은 잠금 파일 자체는 실행 중이라는 뜻이 아니다.
- `gui/services.py:Preview`: 현재 녹화 파일에서 음성 없이 프레임을 5초마다 갱신한다. 출력 버퍼를 고려해 진행 시간 기준 약 8초 이전 위치를 읽는다. 분할 파일이 아직 비어 있으면 최근 읽을 수 있는 파일을 사용한다. 미리보기를 꺼도 녹화는 계속한다.
- `chzzk_record.py:load_config_async()`는 설정 읽기 실패 시 마지막 유효 설정을 유지한다. 설정 저장 도중 활성 녹화가 취소되지 않도록 이 동작을 보존한다.
- `chzzk_record.py:main()`은 종료 시 녹화 정리와 마지막 로그 표시를 처리한다. GUI의 중지/종료도 이 정리 경로를 거쳐야 한다.
- 사용자에게 보이는 문구는 `i18n.py`의 5개 언어를 함께 관리한다. `pyproject.toml`은 Python 3.12 이상이며 PySide6는 `gui` 선택 의존성이다. `uv.lock`은 Qt 6.11.2를 포함한다.

## 현재 논의와 관련 기록

- 사용자 확정 요구사항(2026-09-07): 깔끔하고 누구나 사용할 수 있는 리본 UI, 설정 위에 잠시 포인터를 두면 표시되는 설명, CLI와 GUI를 모두 사용할 수 있는 구조.
- PySide6 + Qt Widgets, 별도 녹화 프로세스, 도움말 700ms 지연을 실제 구현에 사용했다. 사용자가 구체적인 지연 수치를 지정한 것은 아니다.
- 초기에는 사용자가 `리본 시안의 모든 설정 완성`을 선택했고, 이후 실제 구현과 채널 아이콘/현재 녹화 영상 미리보기를 명시적으로 요청했다. 실제 GUI 연결 단계로 범위가 확대되어 구현했다.
- Linux offscreen Qt, 공개 채널 API/프로필 이미지, 합성 TS/MKV/WebM/분할 파일 프레임과 파일 정리를 검증했다. 실제 NAVER 로그인, Windows/macOS, 실제 장시간 CHZZK 녹화 및 하드웨어 인코더는 미검증이다.
- [Qt GUI 설계](plans/qt-gui.md)
- [GUI 설정 대응표](plans/gui-settings-coverage.md)
- [지침 정리, 작업 메모 규칙 및 GUI 구조 검토](worklogs/2026-09-06-ai-notes-qt-gui.md)
- [리본 UI와 도움말 요구사항 반영](worklogs/2026-09-07-ribbon-ui.md)
- [전체 설정 시안 구현과 검증](worklogs/2026-09-07-all-settings-preview.md)
- [실제 Qt GUI, 프로필 이미지와 녹화 미리보기 구현](worklogs/2026-09-08-qt-gui-implementation.md)
