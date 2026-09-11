# GUI 중지 상태와 방송 화질 조회 오류 수정

확인일: 2026-09-11. `gui` 브랜치, 기준 커밋 `772fff4`.

## 요청과 원인

- GUI의 녹화 중지를 누르면 녹화하지 않던 채널까지 종료 중으로 표시되는 문제와 방송이 꺼진 채널의 화질 조회 실패 Traceback을 수정한다.
- `recorder_bridge.py:JsonBridge.display()`가 전체 `shutdown_event`만으로 모든 채널 상태를 `stopping`으로 덮어썼다.
- `chzzk_record.py:record_stream()`에는 이미 OPEN 확인이 있었지만, 별도의 Streamlink 화질 조회 실패를 `RuntimeError`로 다시 던져 일반 녹화 오류/Traceback 경로로 보냈다. 첫 상태 확인과 조회 사이에 방송이 종료되거나 제공 스트림이 일시적으로 없을 수 있다. 사용자 로그만으로 당시 실제 방송 상태를 확정할 수는 없다.

## 변경

- 실제 진행 데이터가 남은 채널만 `stopping`을 표시한다. 중지 요청 시 대기 채널은 `idle`, 비활성 채널은 `inactive`다. 파일 정리 후 진행 데이터가 사라지면 해당 채널도 중지 상태로 전환한다.
- 화질 준비를 방송 대기 루프 안으로 옮겼다. 예상 가능한 조회/화질 선택 실패(ValueError, OSError, TimeoutError)는 방송 상태를 다시 확인한다. CLOSE 등은 방송 대기로 돌아가며, 여전히 OPEN이면 기존 다국어 안내에 채널 이름을 붙여 경고하고 기존 재확인 간격으로 재시도한다.
- `prepare_recording_quality()`는 조회 완료와 중지 요청을 함께 기다리고, 종료·작업 취소 시 조회 작업을 취소한 뒤 자식 프로세스 정리를 기다린다. 최고 화질/FPS 변경 없음은 기존처럼 별도 조회를 생략한다.
- 실패 전에는 파일 생성이나 인코더 실행 단계에 들어가지 않는다. 예상하지 못한 예외의 Traceback은 보존한다. 기존 인코딩, Windows 파이프, 마지막 로그 전달, 설정 읽기/쓰기 경로는 수정하지 않았다.
- 새 번역 키 없이 기존 `gui.quality_unavailable`, 상태 및 방송 대기 문구를 재사용한다. 다섯 언어의 상태 번역을 확인했다.

## 검증

- `.venv/bin/python -m py_compile chzzk_record.py recorder_bridge.py`, Ruff `check --select E9,F`, `git diff --check` 통과.
- 무시된 `.gui-validation/status_quality_check.py`에서 오프라인/차단/인증 대기 시 화질 조회 생략, OPEN→조회 실패→CLOSE 전환, 조회 오류 3종 및 빈 화질 목록의 재시도와 간격, 최고 화질 우회, 예상하지 못한 오류의 진단 보존을 확인했다.
- 같은 검사에서 녹화/대기/비활성/비활성 전환 후 정리 중인 채널의 중지 전·중·후 상태, 마지막 로그 전달, 5개 언어 키를 확인했다. 실제 자식 프로세스를 사용해 중지 및 작업 취소 후 종료 코드와 남은 작업 없음, 분할 JSON/잘못된 JSON/출력 크기 제한/실패 종료 처리를 확인했다.
- Linux 실제 실행과 같은 uvloop 검사와 일반 asyncio 검사를 모두 통과했다. 일반 asyncio의 첫 검사는 샌드박스가 내부 알림 소켓의 `send()`를 EPERM으로 차단해 지연됐다. 앱 없이 최소 subprocess 예제로 재현하고, 외부 네트워크 없이 제한 밖에서 같은 검사를 재실행해 정상 종료(약 0.0002~0.0003초)를 확인했다. 앱 코드에 검증 환경용 우회는 넣지 않았다.
- `.gui-validation/status_quality_pipeline_check.py`: Qt QProcess→JSON bridge→실제 Streamlink `--json` 화질 조회→FFmpeg 분할 녹화를 실행했다. 첫 조회를 의도적으로 실패시킨 뒤 재시도 성공을 확인했고, 실제 녹화/오프라인/비활성 채널을 함께 중지해 각각 `stopping`/`idle`/`inactive` 스냅샷을 확인했다. 중간 상태를 관찰하도록 검사에서만 정리 시간을 1.2초 늘렸다.
- 위 통합 검사에서 Traceback 없음, 화질 재시도 경고 1회, 사용자 중지 이유 기록, 오프라인/비활성 출력 폴더 없음, 모든 저장 분할 파일의 크기 > 0 및 FFprobe 256×144 영상 스트림을 확인했다. 결과: `.gui-validation/status-quality-pipeline-58i1mrzv/`.
- 검사는 임시 설정과 합성 영상을 사용했다. 실제 사용자 설정/쿠키 및 기존 미추적 녹화 폴더는 수정하지 않았다. 검사 스크립트와 산출물은 Git 제외 경로에만 있다.

## 참고 및 남은 범위

- 확인한 외부 설명: [Streamlink JSON CLI](https://streamlink.github.io/cli.html#cmdoption-json), [Python asyncio.wait](https://docs.python.org/3.12/library/asyncio-task.html#asyncio.wait). 구현 판단은 현재 로컬 코드와 실행 결과를 함께 사용했다.
- Windows 실환경, 실제 CHZZK 방송 종료 시점의 네트워크 재현 및 장시간 녹화는 이번에 직접 검증하지 않았다.
- 초기 구현 단계에서는 커밋/푸시를 수행하지 않았다. 이후 게시 요청은 아래를 참고한다.

## 커밋·푸시 요청

- 2026-09-11 사용자가 녹화 수정과 후속 GUI 수정의 커밋·푸시를 명시적으로 요청했다. 기존 `gui` 브랜치에서 녹화 상태/화질 처리와 GUI 폰트/레이아웃을 두 커밋으로 구분한다.
- 게시 직전 변경 Python 컴파일, 녹화 모듈 Ruff E9/F, GUI 모듈 Ruff E9/F/I 및 포맷, `git diff --check`를 통과했다. 기존 실제 프로세스·Qt·FFmpeg 검증 후 녹화 코드는 추가 변경하지 않았다.
- 이 기록과 `chzzk_record.py`, `recorder_bridge.py`를 `fix: distinguish recording shutdown and retry unavailable qualities`로 묶는다. 개인 설정, 기존 녹화와 `.gui-validation/`은 제외하고 `origin/gui`에 게시한다.
