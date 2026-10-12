# 녹화 최종 개선과 5개 언어 업데이트 기록

확인: 2026-10-12. 사용자는 종료 경계·보관 거절·보고서 진단 개선, 날짜별 5개 언어 업데이트 기록, dev 커밋 및 main 일반 병합을 승인했다. 원격 push와 Actions 실행은 이번 요청에 포함하지 않는다.

## 시작 상태와 문서

- main `9ce5929`, dev `8557299`. main의 미커밋 국내·해외 분석 문서를 Git stash에 보존한 뒤 dev에 적용했다. Knowledge 충돌은 dev 구조 설명과 main 등록 이력, 분석 결과를 모두 보존해 해결했다. stash 원본은 병합 완료까지 유지한다.
- 루트 CHANGELOG 5개 언어를 만들고 2026-10-10~11의 dev 9개 커밋과 main 워크플로 등록 이력을 실제 한국 시간 커밋 날짜로 기록했다. 이번 분석·기록 문서는 2026-10-12 항목에 추가했다.
- `.ai/AGENTS.md`에 모든 커밋과 같은 커밋의 5개 언어 기록 갱신을 의무화했다. 자기 해시를 필수로 넣지 않아 기록용 후속 커밋 순환을 피한다. 상세 증거는 기존 분석 작업 기록에 보존한다.

## 진행 상태

- 문서 커밋 `3eccc0b`를 dev에 만들었다. 코드 구현과 아래 검증은 완료했고 dev 코드 커밋 및 main 병합은 아직 진행 전이다. Windows 실제 녹화 종료 검사는 합의대로 후속 검증이다.

## 코드 구현

- `RecordingProcessSandbox`는 실행별 OS 임시 디렉터리에 아직 없는 stop 파일 경로를 준비하고 `--chzzk-stop-file`로 전달한다. 디스크 보관 폴더 장애와 독립된 제어 경로이며 새 시도마다 경로가 달라 이전 중지 요청을 재사용하지 않는다. 일반 중지·앱 종료·task 취소 및 예외 정리는 producer부터 종료한다.
- `ChzzkContinuityReader`는 100ms 간격으로 종료 요청을 감시한다. writer는 먼저 stop_requested를 표시한 뒤 delivery 잠금으로 현재 init·전체 미디어·checkpoint 출력을 끝내고 버퍼를 닫는다. 폴링 전에 다음 조각이 빠르게 시작되는 경쟁 조건은 각 deliver 경계의 stop 파일 검사로 해결했다. RingBuffer의 남은 바이트를 EOF까지 읽고 FFmpeg stdin을 닫는다.
- Streamlink 15초 협력 종료 후 실패 시 5초 강제 정리, FFmpeg 60초 및 전체 90초 예산 유지. 제어 파일 생성/쓰기 실패와 시간 초과는 5개 언어 경고 및 forced_stop 증거를 남긴다.
- `BufferFull.reason`으로 이미 출력한 위치·시간·바이트·개수 한도를 구분한다. `can_store()` bool 계약은 유지한다. 선택적 snapshot buffer_reason은 허용 목록만 전달하며 오래된 v1 snapshot은 호환된다.
- FFmpeg 손상 패킷·partial file을 즉시 감지하고 실행별 종류를 한 번만 기록한다. `ContinuityReport.output_error()`는 녹화기만 작성하며 실행 UTC 시각·채널·검증된 종류 이외 URL·쿠키·원문 예외를 전달하지 않는다. summary 오류에 반영해 FFmpeg exit 0도 실패로 판정한다. 기존 누락·중복·미해결 판정은 유지한다. 요약 안내도 보고서·출력 오류로 5개 언어에서 명확히 했다.

## 로컬 검증

- 코드 커밋 `f3c9212` 이후 main 병합 미리보기에서도 126개 전체 테스트가 통과했다(67.599초). 최종 경로 검토에서 기존 10초 pipe 배출 제한이 작업을 취소하면 정상 종료로 오판할 수 있음을 확인해, 미커밋 병합만 취소하고 dev에서 보완했다. main 쪽 워크플로 수정은 별도 stash로 보존했다. 이전 커밋과 분석 문서는 유지했다.
- 배출 task가 실제로 취소됐으면 `forced_stop`을 추가한다. 배출을 완료했지만 작업이 지연되는 실제 FFmpeg fixture를 시간 초과로 취소하여, 완전한 250 영상 프레임·음성이 있어도 report 오류 1·passed=false로 확인했다. 최종 종료 검사 **12개 통과**, 5.339초(`/tmp/chzzk-stop-final.log`), 문법 및 whitespace 통과. 전체 main 재병합 검사는 보완 커밋 후 다시 수행한다.
- `.venv/bin/python -m unittest discover -s tests -q`: **126개 통과**, 실패·오류·건너뜀 0, 68.250초. 최초 제한 환경에서 소켓을 만들 수 없던 검사는 로컬 HTTP 서버가 허용된 실행에서 재검사했다. 최종 로그 `/tmp/chzzk-dev-all-tests.log`.
- 실제 fMP4→Streamlink reader→Recorder→FFmpeg 검사 4개: 조각 중간 중지, 출력 지연, 복구 대기, task 취소. 수신 바이트는 init+첫 전체 조각과 정확히 일치하고 checkpoint 1개, gap/duplicate/output error 0. 250 영상 프레임 및 음성 프레임 수가 원본 전체 조각과 같으며 모든 패킷 상대 PTS를 MKV 반올림 2ms 이내로 대조했다. 전체 영상·음성 디코딩 오류·경고 0.
- 검사 장치의 RingBuffer.write 반환값은 None이므로 테스트에서 정수로 가정했던 부분을 정정했다. AAC priming에 따른 원본 첫 영상 PTS 38ms 간격을 누락으로 오판하지 않도록 모든 원본/출력 PTS를 직접 대조했다. 정상 코드의 다음 조각 경계 경쟁 조건도 실제 검사에서 찾아 수정했다.
- stop 디렉터리 생성/쓰기 실패·시간 초과·반복 중지·새 시도 경로·임시 폴더 정리, 4종 보관 거절, 선택 필드/기존 v1/민감 데이터 거절을 검사했다. 세 output_error 종류는 연속 checkpoint가 있어도 공백 0·오류 1·passed=false이며 실제 CI 실행기 모의 검사에서도 실패한다.
- 수정 Python 파일 문법 컴파일, Streamlink 8.6.2 CLI의 stop-file 인수 등록, 5개 언어 경고 및 업데이트 기록 링크·날짜/항목 대응, git diff --check 통과. 공식 SHA-256 확인한 actionlint 1.7.12로 두 워크플로 검사 통과(shellcheck/pyflakes 제외).
- 제공 국내 영상의 직접 검사와 해외 보고서 판정은 원래 분석 문서를 따른다. 새 코드의 Windows/macOS 네이티브 종료, 실제 해외 장기 녹화, 새 자연 장애 재현은 수행하지 않았다. 원격 push/Actions는 실행하지 않았다.
