# Rust 부분 도입 검토

확인: 2026-11-15 (Asia/Seoul), `main` / `797820e`.

## 요청과 확인

- 사용자 요청: 이 프로젝트 일부에 Rust를 도입할지 검토.
- 루트 `AGENTS.md`, `.ai/AGENTS.md`, `.ai/codex.md`, 최신 `.ai/KNOWLEDGE.md`를 확인했다.
  루트 `codex.md`는 없고 보충 지침은 `.ai/codex.md`에 있다.
- 시작 작업 트리는 깨끗했다. 현재 `ctx_resume`에는 선행 작업 요약이 없었다.
- Ponytail full 및 이식 검증 설계에 property-based-testing의 비교 기준·입력 생성 원칙을 적용했다.
- GPT-6 Luna 보조 에이전트 두 명이 실행 경로 후보와 배포·테스트 비용을 읽기 전용으로
  나누어 조사했다. 최종 제안은 루트에서 코드와 대조해 통합했다.
- `hls_continuity.py:validate_media`와 호출 6곳, Streamlink 상속·미디어 수신·검증·중지 경계,
  `recording_buffer.py:MediaBuffer`, `continuity_report.py:summarize`,
  `recording_continuity.py:parse_event`, `chzzk_record.py`의 파이프·FFmpeg 실행 경로를 확인했다.
- 설치기·`pyproject.toml`·CI·기존 unittest 및 HLS/버퍼 계획·2026-11-11 작업 기록을 확인했다.
  PyO3/maturin, Python hashlib 및 orjson 공식 자료도 조회했다.

## 판단과 변경

- 직접 관리하는 Rust 빌드 경로는 없으며 `orjson`은 이미 Rust 기반 의존성이다.
- 제품 도입은 실제 병목 측정 뒤 결정하고 작은 실험은 `validate_media`부터 권고했다.
  TS 반복문은 후보지만 fMP4는 박스 본문을 건너뛰므로 실제 전체 성능 이득은 미확인이다.
- 버퍼·HLS 복구 전체·GUI·OS별 파이프는 첫 전환 대상으로 권하지 않는다.
- 제안과 최소 비교 실험·배포 비용·검증 기준을
  [Rust 도입 검토](../plans/rust-adoption-review.md)에 저장했다. 사용자 확정 결정이나 구현 완료가 아니다.
- 제품 코드·설정·의존성·테스트·Git 이력은 변경하지 않았다. 변경은 검토 문서와 이 메모뿐이다.

## 검증 및 남은 작업

- 소스/호출부/기존 테스트/CI 대조와 공식 자료 확인을 수행했다.
- `git diff --check`를 통과했고 신규 문서 두 개의 후행 공백·마지막 개행과
  핵심 참조 함수의 줄 위치도 별도로 확인했다. 최종 변경은 신규 문서 두 개뿐이다.
- Rust 구현·컴파일·성능 측정·회귀 테스트 재실행·실방송·타 OS/Android 검증은 수행하지 않았다.
- 성능 또는 학습 목적에 맞춰 후속 실험 범위를 정하는 단계가 남아 있다.

## 사용자 지시에 따른 시험 구현과 실행

- 사용자가 "그렇다면 테스트 좀 해보자"라고 지시했다. 범위는 위 검토의
  `validate_media()` 한 함수 비교 실험으로 정했고 제품 경로에는 연결하지 않았다.
- `experiments/rust-media-validator/`에 PyO3 Rust 구현, 독립 `pyproject.toml`,
  `Cargo.toml`/`Cargo.lock`, `compare.py`, `regression.py`, 사용법과 측정 JSON을 추가했다.
  Python 제품 코드·설정·루트 `pyproject.toml`/`uv.lock`·기존 테스트는 수정하지 않았다.
- GPT-6 Luna 보조 에이전트가 비교 실행기를 작성하고 루트에서 경계 입력·파일 벤치마크를
  보강했다. 추가 읽기 검토에서 Rust의 범위 검사·판정 동등성과 회귀 실행기 주입 경로를
  확인했다. Unix 전용 `resource` 실행 제약은 README에 명시했다.
- Rust 도구가 없어 공식 rustup 바이너리 SHA-256을 확인하고 `CARGO_HOME`, `RUSTUP_HOME`,
  Python 환경 및 빌드 출력은 `/tmp/chzzk-rust-*`에 두었다. 시스템 설치·셸 설정은 바꾸지 않았다.
  Python 의존성은 기존 `uv.lock`에서 export하고 해시를 검증해 임시 환경에 설치했다.
- 환경: AMD Ryzen 5 5600X, Linux x86_64, Python 3.12.15, Rust 1.100.0,
  PyO3 0.30.1, maturin 1.16.0, 잠금 Streamlink 8.6.2, FFmpeg n9.0.2.
  release/abi3-py312 wheel 빌드·설치·호출을 확인했다. wheel의 Linux 태그는
  `manylinux_2_34_x86_64`이며 배포 호환성 확대 작업은 하지 않았다.

### 검증 결과

- 고정 seed `20261115`, 명시 기대 사례 22개, 임의 바이트 50,000개,
  구조적 TS/MP4 25,000개, 정상 구조의 모든 prefix 260개,
  FFmpeg 생성 TS·init·fMP4 조각 5개, 총 **75,287개**의 허용/거부 및 오류 메시지가 일치했다.
  새로운 Hypothesis/proptest 의존성은 추가하지 않았다.
- 기존 전체 unittest는 Python 기준 **137개 통과**(테스트 73.933초),
  Rust 주입 **137개 통과**(73.955초)다. 부모 실행 전체는 각각 74.233/74.271초였다.
  각 35개 Python 프로세스의 기록을 수집했고 그중 18개에서 실제 검증 호출을 확인했다.
  실제 FFmpeg 프레임·음성·PTS 및 복구·중지 검사를 기존 테스트를 통해 실행했다.
- 시간 계측된 검증은 Python 949회/약 32.3MB/합계 2.958ms,
  Rust 944회/약 31.7MB/합계 0.860ms였다. 경쟁·재시도가 있는 테스트라 호출 수와 바이트 수가
  서로 다르며 이 합계의 비율을 성능 향상 배수로 쓰지 않는다. 계측 오버헤드도 포함한다.
- 최초 기본 샌드박스 실행에서는 로컬 서버를 사용하는 검사들이 오류를 내어 중단했다.
  로컬 서버가 필요한 테스트를 승인된 실행 경로로 다시 실행한 위 결과는 모두 통과했다.
  `/usr/bin/time`도 없어 해당 최초 계측 명령은 시작하지 못했다. 최종 실행기는 Python
  `resource`/`perf_counter`를 사용한다.
- Python 문법 컴파일, Rust `cargo fmt --check`, `git diff --check`를 확인했다.
  실행 로그는 `/tmp/chzzk-rust-{python,rust}-regression.log`,
  전체 프로세스 계측은 같은 이름의 `.json`에 있다. 보존 결과는 실험 폴더의
  `results.json` 및 `regression-results.json`이다.

### 함수 벤치마크와 판단

측정은 다른 검사 종료 뒤 release 확장에서 동일 입력을 재사용하고,
Python/Rust 순서를 교대해 5회 중앙값을 구했다. Python 호출·바이트 인자 전달을 포함한다.

| 입력 | Python/회 | Rust/회 | 배수 |
| --- | ---: | ---: | ---: |
| 합성 TS 약 1MiB | 204.457µs | 2.849µs | 71.76 |
| 합성 TS 약 8MiB | 1,617.660µs | 37.824µs | 42.77 |
| 합성 fMP4 본문 1MiB | 0.627µs | 0.075µs | 8.32 |
| FFmpeg TS 표본 | 36.951µs | 0.519µs | 71.15 |
| FFmpeg fMP4 첫 조각 | 1.240µs | 0.082µs | 15.11 |

- 바이트 루프가 있는 TS에서 함수 자체의 큰 개선을 확인했다. fMP4는 개선 전에도 매우 짧다.
  합성 전체 회귀 검사에서도 검증 함수가 차지한 절대 시간이 작고 전체 소요 시간의
  개선은 관측하지 못했으므로 제품 기본 경로 도입을 권할 근거로 확대하지 않는다.
- 실방송·장시간·실제 다채널 CPU/RSS 프로파일·Windows/macOS/Android는 미검증이다.
  Unix 회귀 실행기는 Windows에서 동작하지 않으며 타깃별 wheel 배포도 준비하지 않았다.
- 이번 요청의 시험 구현·비교·로컬 회귀 검사를 완료했다. 제품 적용은 사용자 결정과
  실제 부하 근거가 필요한 후속 작업이며 커밋·푸시·PR은 수행하지 않았다.

## 지정 방송 실제 녹화 검사

- 사용자 요청: `https://chzzk.naver.com/live/6e06f5e1907f17eff543abd06cb62891`을
  실제 테스트 녹화한다. 현재 공식 API에서 `OPEN`, 비성인, 비인증 playback 가능,
  live ID `22210233`을 확인한 뒤 3분 표본을 진행했다.
- `scripts/run_recording_test.py:write_config/monitor_recording`을 재사용했다.
  개인 설정·인증정보를 읽지 않고 빈 쿠키의 별도 설정을 만들었으며 원본 화질 복사,
  인코더 비활성, 기본 5분 분할을 사용했다. 미디어는 새 비공개 폴더에 보존한다.
- 임시 `sitecustomize`로 Rust 검증기를 실제 Streamlink 자식에 연결하고,
  같은 바이트를 원본 Python 함수로도 판정했다. 불일치는 실행 오류로 처리한다.
  이 과정은 실험 환경에만 적용하고 제품 코드는 수정하지 않았다.
- `monitor 3 90 ... --config ...`가 180초 뒤 JSON stop 명령으로 정상 종료했다.
  강제 종료·버퍼 잔존은 없고 프로젝트 녹화 잠금도 해제된 것을 확인했다.
  모니터 실행 반환 코드는 0이다.

### 결과

- 방송 수신은 한국 CDN LL-HLS, 화질 1080p였다. Akamai LL-HLS `ready` 안내는 있었지만
  실제 대체 출력·장애 복구 성공을 의미하지 않으므로 그렇게 해석하지 않는다.
- 초기 연결 시간을 포함한 모니터 180초에서 실제 녹화는 **164.038초**,
  **1920×1080/60fps H.264 + 48kHz 스테레오 AAC**, 파일 **173,926,320바이트**(약 165.9MiB)다.
- 연속성 보고: 완료 footer 및 checkpoint 82개, `passed=true`,
  gap/unresolved/duplicate/error 각각 **0**.
- 실제 조각 검증 **504회**(init 88회 포함), 누적 검사 바이트 681,971,683,
  Python/Rust 판정 불일치 **0**, 거부 입력 **0**이다. 누적 바이트는 같은 조각의
  여러 검증을 포함하므로 녹화 파일 크기와 구분한다. 3개 Python 프로세스 중
  실제 미디어 검증은 1개 Streamlink 프로세스에서 발생했다.
- 같은 호출에서 측정한 검사 시간 합계는 Rust **0.730ms**, Python **2.704ms**,
  중앙값은 각각 1.200µs/4.905µs다. Rust를 먼저, Python을 다음에 호출한 관측값이며
  이 작은 표본을 일반적인 성능 배수로 쓰지 않는다. Python 프로세스 CPU 합계
  3.004초 및 최대 단일 프로세스 RSS 약 441.5MiB도 기록했지만, Python shadow와
  import 비용을 포함하고 FFmpeg 전체 CPU를 뜻하지 않아 Rust 단독 부하로 해석하지 않는다.
- FFmpeg 전체 디코딩은 반환 코드 **0**, 경고·오류 행 **0**, 비디오 **9,840프레임**이다.
  ffprobe 비디오 packet 9,840개/음성 packet 7,687개에서 PTS 중복·정상 간격의
  1.5배를 넘는 공백·역행 DTS는 각각 0이다. 최대 PTS 간격은 영상 17ms,
  음성 약 21.334ms다. 원본 upstream 전체와 비교한 무손실 증명은 아니다.

### 산출물과 한계

- 보존 위치: `/home/munsy0227/Chzzk-Rekoda/.cache/rust-live-test-20261115-002510/`.
  녹화 `.ts`, `test-result.json`, `continuity-summary.json`, `validator-summary.json`,
  `media-verification.json`, 원본 보고서·프로필·디코딩 로그 및 `test-tools/`를 포함한다.
  `.cache`는 Git 제외 대상이며 폴더 권한은 0700이다. 요청 영상은 삭제하지 않았다.
- 새 검사 도구는 해당 산출물의 `test-tools/`에 보존했고 Python 문법 검사와
  소스·설정·의존성·기존 테스트의 미변경을 확인했다. Knowledge를 갱신한다.
- 실제 방송의 짧은 정상 수신 표본이다. 장시간·의도적 장애·다채널·타 OS와
  Rust 단독 모드의 전체 CPU/RSS 개선은 확인하지 않았다. 실방송에서도 검사 함수의
  절대 소요 시간이 작아 제품 기본 도입에 대한 기존 보수적 권고는 유지한다.

## 방송 감시를 Rust로 옮기는 후속 질문

- 사용자 질문: 실시간 방송 확인 등을 Rust로 만들고 녹화는 기존 방식대로 두면 어떤지.
- 최신 Knowledge와 현재 작업 트리를 확인하고 `get_live_info`, `record_stream`의
  두 상태 조회 호출, `manage_recording_tasks`의 공유 aiohttp 세션과 대기 간격을 읽었다.
- 첫 범위는 대기 채널 관측과 이벤트 전달로 제안했다. 설정·인증·녹화 시작의 최종 확인,
  녹화 세션 소유권·복구·정상 종료는 Python에 남긴다. 감시기 CLOSE/조회 실패만으로
  진행 중인 녹화를 죽이지 않고 중복 시작·오래된 이벤트·감시기 장애를 구분해야 한다.
- 현재도 비동기 공유 HTTP 세션을 사용하므로 Rust 언어 변경에 따른 감지 지연 감소를
  단정하지 않았다. Python GUI/관리자가 상주하면 Rust 프로세스의 총 RSS 비용이 추가될 수 있다.
- 제안은 [기존 Rust 검토 계획](../plans/rust-adoption-review.md)의 후속 절에 저장했다.
  reqwest 비동기 Client/연결 풀 공식 문서도 확인했지만 의존성·구현 변경은 하지 않았다.
- 문서만 변경해 회귀 테스트·실방송·성능 측정은 재실행하지 않았다. 이 방안은 제안 단계다.

## 방송 감시 외 후보 추가 검토

- 사용자 요청: 다른 부분에도 Rust 도입이 좋은 곳이 있는지 확인.
- 최신 Knowledge와 현재 작업 트리를 확인했다. 제품 변경 없이 GPT-6 Luna 두 에이전트가
  미디어 I/O·버퍼·진행 집계와 DNS·OS 파이프·설정·GUI·인코더·로그인을 각각 읽기 검토했다.
  루트는 보고서 분석·호출부와 버퍼의 두 materialize 경로를 추가로 대조했다.
- 추가로 분리하기 쉬운 후보는 `continuity_report.py:summarize`의 오프라인 분석이다.
  대형 입력에서 비용이 확인될 때의 후보이며 녹화 속도 개선이나 현재 병목으로 단정하지 않는다.
  완료·오류 판정·20ms 경계·시간대·반올림은 기존 Python 결과와 비교해야 한다.
- 버퍼 바이트 복사, 분할 파일의 반복 목록/stat, 파이프 중계는 조건부 후보로 분류했다.
  같은 작업을 Rust로 반복하는 것보다 복사·시스템 호출 수를 줄이는 작은 Python 대안이 먼저다.
  복구 후보 검사와 실제 출력의 materialize가 반복되지만 후보 선택 검증의 역할도 있어
  단순 삭제 안전성은 확인하지 않았다. 이번 요청에서 수정하지 않았다.
- Qt/FFmpeg 래퍼, OS 잠금, 설정·로그인 및 Python DNS 연동의 이식 우선순위는 낮다.
  특히 프로세스 감독 확장은 기존 recorder singleton 잠금과 세션 소유권을 먼저 설계해야 한다.
- [Rust 검토 계획](../plans/rust-adoption-review.md)의 추가 모듈 절에 근거와 범위를 저장했다.
  Python hashlib/asyncio, Qt QProcess 공식 문서도 확인했다. 추가 구현·테스트·벤치마크·
  실방송 실행·개인 설정/인증정보 조회는 하지 않았다.

## 전체 후보 측정 지시에 따른 구현·실행

- 사용자 지시: "그냥 다 측정해보자". 감시/보고서/해시·버퍼/중계/분할 파일 집계는
  Python 기준과 Rust 비교 도구로, Qt·설정·DNS·OS·인코더·쿠키 필터는 기존 실행 비용으로
  측정했다. 전 기능의 Rust 제품 포팅을 수행한 것은 아니다.
- 지침·최신 Knowledge·현재 상태를 확인하고 GPT-6 Luna 에이전트 세 명에게
  `experiments/rust-profile/{report,io,watch}/`를 분담했다. 루트는 기존 연결 코드와
  Qt/FFmpeg·CLI/GUI 대기 상태, 결과 통합 및 계측 공정성 검토를 담당했다.
- 신규 Rust 코드는 각 독립 Cargo 프로젝트와 잠금파일에 한정했다. 사용한 비교 의존성은
  serde_json/chrono, sha2/crc32fast, reqwest/tokio/libc 등이며 제품 의존성은 그대로다.
  기존 uv.lock의 GUI extra 및 Ruff만 `/tmp/chzzk-rust-env`에 추가했다.
- Release 빌드와 selfcheck 후 본 측정은 보고서→기존 연결 코드/GUI→대기 프로세스→
  I/O→감시 순서로 분리했다. 메모리/단위 보강에 따른 보고서 재측정도 독립 실행했다.
  폴링 다채널 부하는 localhost fixture만 사용해 실제 CHZZK 부하는 추가하지 않았다.
- 공정성 검토에서 Rust pipe 앞뒤의 Python 중계를 제거하고 OS FD로 연결했으며,
  CRC32는 직접 느린 구현 대신 crc32fast를 사용했다. 해시는 black_box와 반복 측정을 사용했다.
  Python/Rust의 요청 수와 정수 liveId 계약을 맞추고 Python import를 timing 전에 완료했다.
  tracemalloc은 시간 측정과 분리했다. wait4의 동일 RSS 관측은 부모 상속 high-water로
  분류하고 보고서는 worker 자체 VmHWM/VmRSS, 감시는 /proc RSS 표본을 사용했다.
- 최초 감시 full 명령은 debug/release 빌드 위치 불일치로 시작하지 못했다. 경로를 확인해
  release 빌드를 만들고 정수 ID/steady CPU 계측을 보강한 뒤 최종 matrix를 실행했다.
  최초 DNS 자체검사의 relative rrset는 absolute name으로 고쳤다. 최종 검사는 통과했다.

### 주요 결과

- 감시: 1/16/64채널 × 0/20ms 응답 지연 × 언어별 3회, 0.3초 주기 5회,
  총 4,860개의 로컬 요청. 모든 실행의 요청/OPEN/시작 수가 일치했다.
  64채널/20ms에서 약 1.5초 동안 steady CPU는 Python 37.96ms/Rust 23.58ms,
  표본 최고 RSS 중앙값 44.64/14.20MiB였다. 1채널/20ms 첫 OPEN 응답은
  21.07/20.77ms였다. 이 지연은 시작 시 이미 OPEN인 채널의 첫 응답이며,
  실제 폴링 사이 방송 시작의 전체 감지 지연과 구분한다.
- 보고서: 실제 82 checkpoint 및 1k/10k/100k 합성 보고서(공백/중복/오류/미완료/20ms
  경계 포함) 결과 JSON이 일치했다. 입력마다 언어별 5회. 10만 개 처리 중앙값은
  첫 2후보 측정에서 Python 906.32ms/Rust 135.53ms, 프로세스 시작 포함 926.72/136.77ms였다.
  해당 입력의 자체 VmHWM은 14.73/20.16MiB였다. Rust는 전체 파일 읽기,
  Python은 streaming이라는 구현 차이가 있어 Rust 메모리 우위로 일반화하지 않는다.
- 기존 의존성 orjson 대안도 추가 측정했다. `summarize/parse_event` 본문은 유지하고 두 모듈의
  JSON 어댑터만 격리 프로세스에서 바꿔 bytes→str 비용을 포함했다. 3후보 전 입력의 oracle
  parity 후 각각 5회 측정해 최종 10만 개 표준 Python/orjson/Rust 처리는
  929.46/591.53/134.94ms, 시작 포함 949.01/618.84/136.44ms,
  자체 VmHWM 14.75/17.20/20.13MiB였다. 최종 CPU 필드 정의를 명확히 한 5회 측정값이며,
  최초 2후보 원본은
  `report/benchmark-results-stdlib.json`, 최종 3후보는 `report/benchmark-results.json`이다.
- SHA-256 8MiB: Python 결합 복사 4.370ms/update 두 번 3.678ms/Rust 내부 3.537ms.
  모든 digest가 같고 Rust 내부 20회와 프로세스 전체 시간을 분리해 기록했다.
- 실제 MediaBuffer 8MiB warm SSD: store/load/두 materialize가 5.62/5.55/9.76ms.
  별도 추적 할당은 약 8/16/16MiB. 단순 복사+CRC 비교는 Python 5.36ms/Rust 3.99ms지만
  Rust 쪽에 버퍼 정책·메타데이터·SHA·잠금이 없어 전체 버퍼 포팅 배수로 쓰지 않는다.
  tmpfs(`/tmp`)와 SSD 각각 1/8MiB를 측정했다.
- 256MiB 파이프 3회 중앙값: 기존 Python 230.5ms/Rust 178.5ms/OS 직결 196.6ms.
  전체 경로의 합산 CPU는 420.8/267.2/250.5ms. 동일 count/CRC/종료 코드 및
  Python/Rust 느린 sink의 역압력/EOF가 통과했다. 실방송 녹화 배수로 해석하지 않는다.
- 분할 파일 기본 100/1k/10k 및 경계 파일로 목록/최종 합계 일치. 1만 개는
  Python 45.85ms/Rust 23.36ms/Python 경로 목록 캐시 22.20ms였다.
  캐시는 변경 없는 snapshot 실험이며 실제 적용에는 생성·이름 변경·삭제 갱신이 필요하다.
- 기존 연결 코드 20개 항목: 64채널 설정 정규화 260µs, fsync 포함 저장 7.45ms,
  OS 잠금 11.7µs, DNS hit 0.72µs/wire decode+검증 45.0µs,
  녹화 이벤트 파싱 4.76µs, 인코더 probe 39.54ms/캐시 0.44µs,
  Qt 미리보기 128.99ms/같은 FFmpeg를 Rust로 실행하는 경로 135.30ms였다.
  미리보기 JPEG 해시가 같고 Rust 디코더가 아닌 실행기 비교임을 명시했다.
- 빈 설정 CLI/GUI 8초 대기에서 안정 RSS 표본은 약 50.9/90.3MiB.
  offscreen GUI이며 데스크톱 등록·실사용 설정을 사용하지 않았다.

### 검증·산출물·남은 범위

- [전체 측정 보고서](../../experiments/rust-profile/README.md) 및 같은 폴더 `summary.json`에
  통합했다. 하위 폴더 raw JSON에는 모든 반복값·CPU·단위·메모리 범위가 있다.
- 각 Rust release 빌드·oracle selfcheck·요청수/상태 전이·digest/count/EOF·파일 합계
  검증을 완료했다. Python compileall, Ruff format/기본 검사, cargo fmt 및 diff 확인을 통과했다.
  제품 소스·루트 의존성·기존 테스트가 그대로여서 이전 137개 회귀 검사는 재실행하지 않았다.
- root README와 Knowledge/계획을 갱신했다. 커밋·push·PR·기본 녹화 동작 변경은 하지 않았다.
- 실제 로그인/개인 쿠키/외부 DoH TLS 왕복·Windows/macOS·장시간/실다채널 녹화는
  이번 계측 범위 밖이다. 보고서 Rust parser의 RFC3339/i64 한계와 파일 패턴의 ASCII
  숫자 한계도 보존했다. 전체 앱을 Rust로 전환한 CPU/RSS/품질 검증으로 해석하지 않는다.
