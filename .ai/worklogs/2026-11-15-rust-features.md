# Rust 기능 브랜치 구현

- 확인일: 2026-11-15 (Asia/Seoul).
- 요청: 전체 후보 측정 후 Rust 기능 브랜치를 만들고 실제 코드 작업.
- 브랜치: `main`의 `797820e7e8d87ea598ef8064a3e9b5cdb62733aa`에서 `codex/rust-features` 생성. 기존 실험·문서 변경을 보존했다. 커밋·push·PR은 수행하지 않았다.

## 구현

- `native/Cargo.toml`, `Cargo.lock`, `src/main.rs`, `watch.rs`, `report.rs`: 선택형 실행 파일. `serve`는 버전 1 JSONL로 고정 CHZZK live-detail endpoint를 조회한다. 헤더는 private pipe로만 전달하며 오류는 정적 분류/HTTP 상태만 반환한다. redirect/proxy 자동 적용을 끄고 요청 30초, 병렬 HTTP 16개·대기 포함 64개, 입력 64KiB·본문/출력 8MiB 상한을 둔다. cancel과 stdin EOF에서 진행 요청을 중단한다.
- `native_backend.py`: release/bin 실행 파일 자동 발견, handshake·동시 응답 매핑·취소·시간 제한·자식 정리. helper 부재/손상 시 기존 Python으로 대체한다. 정상 HTTP·네트워크 실패는 중복 요청하지 않는다. `chzzk_record.py`는 하나의 helper를 관리하며 DoH 사용 시 생성하지 않는다. 녹화 task 정리 후 helper가 종료된다. 회원 전용 권한·쿠키 검사는 기존 Python 로직을 유지한다.
- `continuity_report.py:summarize_file()` 및 `scripts/run_recording_test.py`: 256KiB 이상만 native report를 시도한다. streaming 입력과 Python 호환 판정, 결과 구조 검증을 사용한다. 넓은 정수·일부 ISO/부동소수 표기·크기 경계·실행 실패는 Python 원본으로 대체한다. `summarize(lines)` 계약은 바꾸지 않았다.
- 보고서 검토에서 윤초, 소문자 `z`, 먼 날짜 timestamp 반올림, JSON 이벤트 길이의 공백/DEL 문자, snapshot window 누락 차이를 발견해 보완했다.
- `i18n.py` 5개 언어 메시지, 5개 README와 `native/README.md` 빌드/동작 안내. CI는 Rust 있음/없음 matrix로 검사하도록 수정했다. Python 제품 의존성과 설정 형식은 유지했다.
- `tests/test_native_backend.py`, `test_native_recording.py`, `test_native_report.py`: IPC·fallback·429 재요청 방지·인증·DoH·종료 순서·실제 hello/EOF 및 Python oracle 검사. 기존 CI 테스트의 임시 복사 목록에 `native_backend.py`와 `process_utils.py`를 추가했다.

## 검증

- Linux, Python 3.12.15, Streamlink 8.6.2 및 잠금 의존성, Rust 1.100.0 release. Rust 도구는 공식 rustup 체크섬 검증 후 `/tmp`에 설치했다. 재개 중 `/tmp` 환경이 없어져 도구를 복원하고 프로젝트 `.venv`에 `uv sync --locked --extra gui`를 수행했다.
- 최종 Rust 단위 검사 12개 통과. `cargo fmt --check`, 수정 Python 문법 컴파일, 새 연결/테스트 파일 Ruff, `git diff --check` 통과.
- Rust 연결 집중 검사 25개 통과. 전체 첫 검사 156개 중 임시 프로젝트 복사 목록 누락으로 failures 2/errors 1을 발견했다. 목록 수정 뒤 해당 검사 및 종료 통합 검사 8개 통과. 최종 전체 회귀 검사 162개가 71.945초에 모두 통과했다. 소문자 시간대 fallback까지 포함한 최종 보고서 oracle 검사 9개도 다시 통과했다. 로그는 `.cache/native-full-tests.log`, `native-focused-tests.log`, `native-report-tests.log`, `native-cargo-test.log`에 있다.
- 10만 체크포인트(19,500,101 bytes) 실제 파일의 native 결과, Python 원본, 파일 진입점 결과가 일치했다. 단일 smoke 실행 0.891초(Python) / 0.264초(native subprocess 포함). 반복 벤치마크나 앱 전체 개선치가 아니다. 자료: `.cache/native-report-check.json`, `.cache/native-report-100000.jsonl`.
- 사용자가 지정한 공개 채널로 빈 쿠키 설정에서 120초 실방송 테스트를 수행했다. Rust 활성 로그와 실제 native live API OPEN 응답을 확인했다. 기존 Streamlink/FFmpeg 정상 종료, 1920×1080 60fps H.264/AAC 영상 126.043334초·133,388,256 bytes 저장. 연속성 checkpoint 63개, gap/duplicate/unresolved/error 0, passed true. 전체 영상·음성 디코딩 exit 0, warning 로그 0 bytes.
- 실방송 자료: `.cache/native-live-test-20261115-021128/`의 `continuity-summary.json`, `test-result.json`, `decode.log`, TS 영상. 개인 설정과 인증 정보는 읽지 않았다.
- 자동 승인 검토 사용량 제한으로 재검증 명령 한 번이 실행되지 않았으며, 사용자 재개 지시 후 검토가 정상화되어 필요한 검사를 재시도했다.

## 남은 확인 범위

- 원격 GitHub Actions 실행, Windows/macOS 직접 빌드·실행, 실제 로그인/회원 방송, 장시간·다채널·실서비스 장애 주입은 미검증.
- 선택형 Rust 자동 설치/플랫폼별 바이너리 배포는 이번 범위에 포함하지 않았다. Python 프로세스는 계속 상주하므로 Rust 전용 감시기 벤치마크의 RSS 절감이 앱 전체에서 그대로 실현되지는 않는다.

## 추가 검증·README·장시간 Actions 및 게시 요청

- 사용자가 추가 확인 후 README 갱신, 커밋·push와 기존 장시간 Actions 수정을 요청했다. Ponytail full을 유지하고 문서·워크플로·독립 검토를 분담했다.
- `native/src/report.rs`가 CRLF 행 끝을 Python 파일 읽기와 동일하게 계산하도록 수정했다. 단독/내부 CR는 원본 Python으로 대체한다. 실제 8,192자 경계 파일과 CRLF/CR를 비교했다.
- Rust의 redirect 거절과 기존 aiohttp redirect 처리 차이를 확인했다. `native_backend.py`에서 3xx 응답은 helper를 중지하고 Python으로 대체한다. 쿠키를 Rust가 redirect 대상에 전달하지 않으며, 일반 429 등 오류는 여전히 중복 요청하지 않는다.
- `NativeWatch`는 수동 녹화 중 실제 별도 Rust 클라이언트를 계속 사용한다. private IPC·빈 쿠키 헤더를 재사용하고, 분당 조회 횟수·성공·HTTP/네트워크/응답 오류·helper 실패만 집계한다. 기록 자체는 정상이고 최초 조회만 성공한 뒤 일시적 HTTP 오류가 발생한 경우와 helper 손상을 구별한다. thread 예외는 종류만 저장하고 URL/예외 원문은 저장하지 않는다. 시작/작업 종료/강제 정리 경로에서도 요약을 보존한다.
- 두 수동 workflow에 Rust/Python 선택(기본 Rust), 필요 시 Cargo 검사·빌드, native 필수 판정과 새로운 artifact를 연결했다. 기존 OS/방송/시간 입력과 5분 분할·15분 영상 정리·7일 artifact 보관 정책을 유지한다. push/PR은 Linux Python 단독/Rust 전체 suite와 Windows·macOS의 Cargo 및 연결/보고서/CI 실행기 검사를 구성했다.
- 5개 언어 README와 CHANGELOG, `native/README.md`를 갱신했다. 시작부터 실행 파일이 없을 때의 조용한 Python 사용과 사용 중 helper 장애 후 대체 로그를 구분하고, DoH 사용 시 Rust live helper를 생략하는 점을 명시한다.
- 추가 집중 검사 41개, 최종 전체 검사 169개(73.095초), Rust 12개 통과. 실제 helper에 32개 동시 요청 × 32회(1,024회 hello)를 보내고 pending state 정리와 종료를 확인했다. Python 문법 컴파일, Rust fmt, 새 파일 Ruff와 수정된 실행기의 import/오류 검사, workflow YAML 파싱과 `git diff --check`도 통과했다. 로그는 `.cache/rust-additional-tests.log`, `rust-final-full-tests.log`, `native-cargo-test.log`에 있다.
- 지정 공개 채널을 재확인했으나 `CLOSE`여서 추가 실방송 녹화는 시작하지 않았다. 이전 120초 녹화의 결과는 위 항목을 유지하며 새 검증으로 대체하지 않는다. 실제 지속 조회 결과는 `.cache/native-additional-watch-summary.json`과 `rust-additional-watch.log`를 확인한다.
- 130초 실제 지속 조회는 총 3회 중 성공 2회·네트워크 오류 1회, helper 실패 0회였다. 이후 조회까지 연결을 유지하고 정상 종료했으며 native health 판정은 통과했다. 임시 검증 스크립트의 최초 '세 번 모두 외부 요청 성공' 조건은 실패했으므로 이를 무오류 네트워크 결과로 주장하지 않는다. 일시적 네트워크 실패를 별도 집계하고 다음 폴링을 유지하는 제품/Actions 정책은 통과했으며 원인은 분류 이상의 증거가 없어 확정하지 않았다.
- `experiments/`의 36개 파일을 게시 전 검토했다. 소스·잠금파일·설명과 원시 benchmark JSON(최대 약 2MB)이며 비밀키·개인 설정·빌드 바이너리·실방송 로그가 없었다. 결과 README가 참조하는 재현 근거이므로 이 Rust 작업의 커밋에 포함한다. `.cache`와 `target`은 제외한다.
- 게시 대상은 `origin`의 `codex/rust-features`이고 같은 이름의 원격 브랜치는 게시 전 없었다. GitHub 인증·workflow 권한을 확인했다. 사용자가 요청한 push 뒤 자동 실행된 원격 결과는 해당 Actions run과 최종 응답에서 확인하며, 수동 5시간 실행은 설정 완료와 구분한다.
