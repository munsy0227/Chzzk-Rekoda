# 수동 녹화 CI 채널 UUID와 최신 안정 OS

확인: 2026-10-11. 사용자 요청: Long recording test와 Codec smoke test의 트리거에서 채널 UUID를 선택 입력하고, 미입력은 기존 채널로 녹화하며 Windows/macOS도 선택 실행한다. 사용자는 OS 선택의 Linux 기본값과 GitHub `*-latest` 안정 이미지 기준을 선택한 뒤 [전체 계획](../plans/recording-test-platforms.md)의 구현을 승인했다.

## 실제 변경

- 두 `.github/workflows/*-test.yml`에 `channel_uuid`와 `test_os=linux/windows/macos/all`을 추가했다. 빈 문자열·공백은 기존 `64a90ba95d1f9feb0a798a20bbf0f40c`로 대체하고 입력된 UUID는 32자리 16진수로 검사·소문자 정규화한다. 입력은 환경변수로 전달하며 shell 코드에 삽입하지 않는다.
- `ubuntu-latest/windows-latest/macos-latest` matrix와 `fail-fast: false`로 전체 선택 시 OS별 병렬 실행을 구성했다. 기존 장시간/코덱 시간 범위·기본값·job timeout·공용 concurrency·uv sync --locked를 유지했다.
- `scripts/run_recording_test.py`에 입력 검증, 설정 생성, 실방송 사전 확인, 인코더 최소 실행, 공통 녹화 감시와 codec/연속성 판정을 모았다. Python 현재 실행 파일로 녹화기를 직접 띄우고 stdout 이벤트를 지속 소비하며 GUI 제어 파이프의 stop 명령으로 정상 종료한다. 120초 초과 시 Windows taskkill /T /F 또는 POSIX 하위 PID/별도 process group까지 종료하고 실패한다.
- Bash helper는 기존 세 인수로 Python monitor를 실행하는 래퍼다. GNU timeout/find -printf/jq에 의존하지 않는다. 종료 보고서 footer 저장 이후 판정하며 무출력·조기 종료·FFmpeg 오류·빈 출력·연속성 실패 기준을 유지한다. 종료 정리 대기 시간은 요청 녹화 시간의 조기 종료 판정에 더하지 않는다.
- 테스트 설정과 녹화 로그는 runner 임시 폴더에 둔다. 저장소 개인 config.json과 로그를 덮어쓰지 않는다. 5분 분할, 180초 무출력 제한, 15초 감시와 60초 정리, 수정된 지 15분이 지난 영상만 삭제하는 정책을 유지한다. JSONL/요약/TXT는 정리 대상이 아니다.
- H.264 원본 복사, libx265/ultrafast, libsvtav1/13을 유지했다. 코덱 테스트 종료 상태가 실패해도 해당 codec 로그를 보존한다. ffprobe JSON에서 동일 코덱 중복 메타데이터를 합쳐 검사하고 빈/불일치 결과는 실패한다.
- `scripts/install_ffmpeg_ci_windows.ps1`은 Gyan release full .7z와 .sha256을 받아 검증하고 7z로 추출한 뒤 ffmpeg/ffprobe 경로를 GITHUB_PATH에 추가한다. essentials에는 libsvtav1이 없어 CI에 full을 사용한다. 기존 사용자 설치기는 변경하지 않았다.
- 항상 업로드하는 아티팩트 이름에 matrix runner/run ID/run attempt를 넣고 보존기간 7일을 유지했다. 로그·JSONL·집계 JSON·실제 OS/이미지/아키텍처/Python/FFmpeg 버전을 포함하며 설정·영상은 업로드하지 않는다. Linux 배포판 정보도 기록한다.
- 새 CI 안내 20개를 i18n.py의 다섯 언어로 추가했고 CI 기본 언어는 en이다. README 다섯 언어, 프로젝트 Knowledge와 승인 계획을 갱신했다. 기존 helper 검증을 래퍼에 맞춰 바꾸고 생명주기 회귀 테스트를 추가했다.

## 수행한 검증

- `.venv/bin/python -m unittest discover -s tests -v`: **115개 통과, 실패·오류·건너뜀 0**, 62.547초. 최초 제한 환경에서 로컬 모의 HTTP 서버 생성이 PermissionError로 차단된 77개는 로컬 소켓 실행이 허용된 환경에서 재검사해 모두 통과했다. 로그는 `/tmp/chzzk-ci-tests.log`에 있다.
- 종료 시간 계산 보정 뒤 최종 CI 테스트 9개와 기존 Bash helper 테스트 1개를 다시 검사해 통과했다. 정상/공백/불완전 보고서/조기 종료/무출력/빈 출력/FFmpeg 오류/시작 실패, stdout 1MiB 소비, 실패 로그 보존을 확인했다.
- 별도 session의 실제 하위 프로세스를 만든 모의 녹화기에 종료 시간 초과를 주입해 강제 정리·실패 요약을 확인했다. Windows taskkill 호출 범위는 모사 검증이며 Windows OS에서 직접 실행한 결과가 아니다.
- 실제 Linux 녹화기를 빈 채널 설정으로 실행해 JSON 파이프 stop, 종료 코드 0, stopped 이벤트와 complete=true 보고서 footer를 확인했다. 실방송/API 요청 없이 수행한 제어 경로 검사다.
- 실제 FFmpeg n9.0.2로 libx265/ultrafast 및 libsvtav1/13의 128x128·2프레임 최소 인코딩 통과. SVT-AV1 4.2.0은 preset 13을 11로 매핑했다. 진단 로그와 환경 JSON은 `/tmp/chzzk-ci-probes/`에 있다. actual codec 메타데이터 검증의 중복/불일치/영상 없음은 모사 검사다.
- actionlint 1.7.12로 두 워크플로 문법 통과(shellcheck는 사용하지 않음). YAML에서 네 OS 선택의 matrix 1/1/1/3개, 입력 기본값과 항상 업로드·OS별 이름을 별도로 검사했다. Python 수정 파일 4개 문법 컴파일, Bash 문법, CLI --help/기본 입력 검증, git diff --check 통과.
- 환경 정보는 FFmpeg가 없어도 OS/이미지/버전을 남기는 모사 검사와 실제 Linux 배포판·FFmpeg/ffprobe 버전 저장 검사를 통과했다. 공백·한글 경로는 실제 로컬 파일/자식 인수로 검증했다.
- GitHub runner 정책, Homebrew FFmpeg 의존성, Gyan full의 libsvtav1 포함, Windows 실행 이미지의 7zip 제공을 공식 자료로 확인했다. 참조: [runner 정책](https://github.com/actions/runner-images/blob/main/README.md), [Windows 이미지](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md), [Gyan](https://www.gyan.dev/ffmpeg/builds/), [Homebrew](https://formulae.brew.sh/formula/ffmpeg).

## 미검증 및 다음 확인

- Windows/macOS 네이티브 실행, Windows full FFmpeg 다운로드·설치와 PowerShell 실행, 실제 세 OS 실방송/장시간 Actions는 아직 미검증이다. OS별 정상 종료·인코더 성능·자연 장애는 원격 실행에서 확인해야 한다.
- GitHub latest는 GitHub의 안정 이미지 기준이며 OS 공급자의 최신 출시판과 다를 수 있다. 버전 전환 후에는 아티팩트 환경 정보와 Set up job 로그를 기준으로 비교한다.
- 커밋·push·원격 Actions 실행은 하지 않았다. 로컬 의존성·잠금파일·인증 정보·개인 설정을 변경하지 않았다.

## 후속 로컬 커밋 요청

- 사용자가 구현 결과 확인 후 로컬 커밋을 요청했다. 두 워크플로, 공용 실행기·Windows 설치기·호환 래퍼, 회귀 테스트, 다섯 언어 안내와 관련 `.ai/` 문서의 16개 파일을 한 논리 단위로 묶는다.
- 커밋 준비 시 작업 트리와 기존 검증 기록을 확인했고 `git diff --check`를 다시 통과했다. 구현 코드는 추가로 바꾸지 않았다. 최근 커밋의 관례에 따라 author/committer는 Codex로 지정하고, 영어 제목과 변경 이유·영향·검증 범위의 본문을 사용한다.
- 요청 범위는 로컬 커밋까지다. push와 원격 Actions 실행, Windows/macOS 실녹화 검증은 별도 요청으로 남는다.
