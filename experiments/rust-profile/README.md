# Rust 후보 전체 측정

확인: 2026-11-15, Linux x86_64 / Ryzen 5 5600X / Python 3.12.15 /
Rust 1.100.0 **release**. 제품 코드·루트 의존성·사용자 설정은 변경하지 않았다.
이 폴더의 Rust 구현은 비교용이며 녹화기에 통합되지 않았다.

전체 수치: [summary.json](summary.json).
원시 반복값: [감시](watch/results.json), [보고서](report/benchmark-results.json),
[I/O](io/results.json), [기존 연결 코드](glue-results.json), [대기 프로세스](idle-results.json).

## 판단

1. **방송 감시:** 독립 감시 프로세스의 CPU/RSS는 Rust가 작았다. 기존 Python/GUI를
   계속 띄우는 구조에서는 해당 Python 메모리가 그대로 절약되는 것은 아니다.
   대기 중 Python 녹화 관리자를 종료하는 구조까지 설계할 때 이점이 생길 수 있다.
2. **보고서 분석:** 큰 입력에서 처리 시간이 크게 줄었다. 현재의 작은 보고서는 기존
   Python도 약 1ms라 사용자가 체감할 필요성은 낮다. 대형 보고서용 별도 도구 후보다.
3. **파이프:** Rust 중계가 빨랐고 CPU도 줄었다. Python 데이터 중계를 생략한 OS 직결은
   합산 CPU가 더 작았다. Rust 채택에 앞서 프로세스 연결 구조의 개선을 검토할 수 있다.
4. **해시·파일 집계:** Python의 결합 복사·반복 목록 조회를 줄이는 대안이 Rust에 근접했다.
   Rust가 있어야만 얻을 수 있는 개선으로 판단하지 않는다.
5. **미리보기·설정·DNS 등:** 기존 네이티브 작업/네트워크/파일 저장이 남는다.
   현재 측정만으로 이식 우선순위를 높일 근거는 부족하다.

## 방송 감시

별도 localhost API에서 1/16/64채널, 응답 지연 0/20ms, 동시 요청 16개,
0.3초 주기 × 5회, Python/Rust 각각 3회 반복했다. 총 4,860요청을 로컬로 보냈다.
실제 CHZZK에 다채널/고빈도 부하를 주지 않았다.
현재 `get_live_info` 함수 본문을 AST로 추출한 Python과 reqwest/tokio 시험 구현이다.
양쪽 요청 수·OPEN 수·방송별 시작 수가 일치한다. 정수 liveId, CLOSE→OPEN 전이,
반복 OPEN, HTTP 500/429, timeout, 잘못된 JSON도 별도 fixture에서 확인했다.

아래는 20ms 응답 지연 시 중앙값이다. CPU는 초기화 이후 약 1.5초 동안의 프로세스 CPU다.

| 채널 | Python CPU | Rust CPU | Python/Rust RSS 표본 최고값 | 첫 OPEN 응답 Python/Rust |
| --- | ---: | ---: | ---: | ---: |
| 1 | 2.58ms | 1.08ms | 44.7 / 12.5MiB | 21.07 / 20.77ms |
| 16 | 11.09ms | 7.95ms | 44.6 / 13.4MiB | 24.09 / 22.74ms |
| 64 | 37.96ms | 23.58ms | 44.6 / 14.2MiB | 56.56 / 65.77ms |

`first_open_response_ms`는 **측정 시작 때 이미 OPEN인 채널의 첫 응답 시간**이다.
폴링 사이에 방송이 시작되는 전체 감지 지연이나 실제 서비스 지연으로 해석하지 않는다.
조회 주기가 같으면 언어 변경만으로 그 대기 시간이 줄어들지 않는다.
쿠키·회원 접근·설정 변경·녹화 소유권까지 구현한 제품 감시기는 아니다.

## 연속성 보고서

파일 읽기·JSON/이벤트 검증·시간 비교·공백 병합을 포함한 처리 시간 중앙값이다.
실녹화 보고서 및 경계/오류 사례가 포함된 합성 보고서를 기존 `summarize`와 비교했다.
각 입력을 후보별 5회 실행했으며 요약 JSON이 일치했다.

| 입력 | Python 표준 JSON | Python + 기존 orjson | Rust |
| --- | ---: | ---: | ---: |
| 실제 보고서, checkpoint 82개 | 0.964ms | 0.669ms | 0.201ms |
| 합성 checkpoint 1천 개 | 9.911ms | 6.507ms | 1.507ms |
| 합성 checkpoint 1만 개 | 93.883ms | 62.191ms | 15.139ms |
| 합성 checkpoint 10만 개 | 929.464ms | 591.535ms | 134.939ms |

기존 orjson 대안은 `summarize`와 `parse_event` 본문을 유지하고 해당 두 모듈의 JSON
입출력만 측정 프로세스 안에서 교체했으며 bytes→str 비용도 포함한다. 세 후보의 결과가 같다.
이 shim 역시 임의 정수·비유한 수 등 모든 입력에서의 제품 호환성을 주장하지 않는다.

10만 개의 프로세스 시작·출력까지 포함한 전체 시간은 표준 Python/orjson/Rust가
949.0 / 618.8 / 136.4ms였다. 자체 VmHWM은 14.8 / 17.2 / 20.1MiB였다. Rust 시험 구현은
파일 전체를 메모리에 읽고 Python은 줄 단위로 처리하므로 Rust의 메모리 우위를 주장하지 않는다.
프로토타입의 Rust 시간 입력은 RFC3339, liveId는 i64 범위여서 Python의 모든 허용 입력을
대체하는 제품 구현은 아니다. [범위](report/README.md)를 참고한다.
최초 2후보 측정 원본도 [별도 JSON](report/benchmark-results-stdlib.json)에 보존했다.

## 해시·복구 버퍼

| SHA-256 입력 | Python 결합 후 해시 | Python update 두 번 | Rust 내부 해시 |
| --- | ---: | ---: | ---: |
| 1MiB | 0.582ms | 0.568ms | 0.454ms |
| 8MiB | 4.370ms | 3.678ms | 3.537ms |

digest가 모두 같다. Rust는 sha2, Python은 hashlib을 사용한다. Rust 내부 값은
이미 읽은 입력의 해시 반복 시간이며 실행파일 시작/입력 파일 읽기/hex 출력은 제외한다.
Rust 8MiB × 20회 배치의 프로세스 전체 시간은 78.5ms였다. 매 해시마다 실행파일을
띄우는 설계의 이득으로 해석하지 않는다.

실제 Python `MediaBuffer`는 1/8MiB를 tmpfs(`/tmp`)와 SSD의 warm page cache에서 측정했다.
SSD 8MiB의 store/load/두 번 materialize는 5.62 / 5.55 / 9.76ms였다.
별도 메모리 패스에서 store는 약 8MiB, load/materialize는 약 16MiB의 Python 추적 할당
최고값을 보였다. load/materialize 측정에는 반환 바이트의 결과 비교도 포함된다.

단순 파일 복사+CRC32의 SSD 8MiB Python/Rust 값은 5.36 / 3.99ms였다.
이는 전체 MediaBuffer 이식 비교가 아니다. Rust 쪽은 방송 귀속·용량 제한·메타데이터·
SHA-256·잠금·정리 정책을 구현하지 않았고 버퍼 전체의 개선 배수로 쓰지 않는다.
복구 후보 검사와 전달 직전 검사에서 반복 읽기가 있어도 후보 선택 의미를 보존해야 한다.

## 파이프 중계와 파일 크기 집계

256MiB 동일 입력을 동일 producer/sink 사이에서 전달했다. 3회 반복의 중앙값이며
모든 경로의 길이·CRC32·종료 코드가 일치했다. 8MiB 느린 sink로 Python/Rust의 역압력과
EOF도 확인했다. 프로세스 시작과 producer/sink 실행을 포함한 전체 경로 비교다.

| 경로 | 전체 시간 | 합산 CPU |
| --- | ---: | ---: |
| 기존 Python 중계 | 230.5ms | 420.8ms |
| OS 파이프로 연결한 Rust 중계 | 178.5ms | 267.2ms |
| producer→sink OS 파이프 직결 | 196.6ms | 250.5ms |

합산 CPU는 여러 프로세스가 병렬로 사용한 CPU를 더하므로 wall 시간보다 클 수 있다.
실방송처럼 입력을 기다리는 경우의 녹화 처리량 향상이나 현재 정상 중지 호환성을
증명하는 검사는 아니다. Windows overlapped 파이프는 이 Linux 시험에 포함하지 않았다.

파일 집계는 기본 분할 파일과 빈 파일·큰 인덱스·이름 변경·비일치 파일을 만들고
Python/Rust의 정렬 결과 및 최종 크기 합계가 같은지 확인했다.

| 기본 파일 수(경계 파일 추가) | 기존 Python | Rust 실행파일 | Python 경로 목록 캐시 |
| --- | ---: | ---: | ---: |
| 100 | 0.582ms | 1.151ms | 0.266ms |
| 1천 | 3.868ms | 3.498ms | 2.550ms |
| 1만 | 45.851ms | 23.360ms | 22.198ms |

목록 캐시는 동일 snapshot에서 정렬·열거를 생략한 비교다. 제품 적용에는 파일 생성·
이름 변경·삭제 시 갱신이 필요하다. Rust 이름 패턴은 ASCII 숫자로 한정했고 Python이
허용하는 Unicode 숫자 이름은 비교 범위 밖이다. 캐시를 비우는 권한 작업은 하지 않았다.

## 기존 연결 코드·네이티브 작업

| 작업 | 기존 실행 시간 중앙값 |
| --- | ---: |
| 설정 정규화 1 / 16 / 64채널 | 66 / 118 / 260µs |
| 설정 저장 64채널, fsync·replace 포함 | 7.45ms |
| 설정 읽기 64채널 | 444µs |
| OS 파일 잠금 acquire/release | 11.7µs |
| DNS 캐시 hit | 0.72µs |
| DNS wire decode + 검증 | 45.0µs |
| DoH HTTP 32KiB Content-Length / chunked 파싱 | 4.25 / 7.64µs |
| 녹화 이벤트 JSON 파싱·검증 | 4.76µs |
| 합성 NAVER 쿠키 필터 | 0.84µs |
| 인코더 인수 생성 | 0.56µs |
| 실제 FFmpeg 인코더 probe / 캐시 hit | 39.54ms / 0.44µs |
| Qt JPEG decode | 1.27ms |
| 기존 Qt→FFmpeg→Qt 미리보기 | 128.99ms |
| Rust 실행기→같은 FFmpeg→같은 Qt decode | 135.30ms |

미리보기 JPEG 출력 해시가 같다. Rust FFmpeg/디코더 구현과 비교한 것이 아니라 기존
FFmpeg 앞에 실행기를 둔 전체 경로다. 외부 timeout에서는 해당 프로세스 그룹을 정리한다.
기존 Python 연결 코드와 Qt/OS/FFmpeg 자체 작업을 섞어 Rust의 순수 계산 이득으로 해석하지 않는다.

빈 테스트 설정으로 8초 대기한 CLI/Qt GUI의 안정 RSS 표본 중앙값은 약 50.9 / 90.3MiB였다.
GUI는 offscreen이며 데스크톱 등록은 실행하지 않았다. 실제 화면/GPU 비용이나 프로세스 트리의
PSS 합계가 아니다. 설정·로그인·DNS는 별도 Rust 대조 구현이 아니라 기존 비용 측정이다.
실제 계정 로그인이나 외부 DoH TLS 왕복·Windows/macOS 네이티브 실행은 하지 않았다.

## 재실행과 해석

독립 도구의 빌드·실행은 [감시](watch/README.md), [보고서](report/README.md),
[I/O](io/README.md)를 참고한다. 이 세 Cargo 프로젝트는 각각 `--release --locked`로 빌드한다.
Python은 기존 uv.lock의 의존성과 GUI extra를 가진 격리 환경을 사용한다.
추가 Ruff는 실험 환경의 형식 검사 도구이며 제품 의존성에 추가하지 않았다.

이 세션에서 실행한 주요 명령:

```sh
/tmp/chzzk-rust-env/bin/python experiments/rust-profile/report/bench.py --benchmark --rounds 5 --output experiments/rust-profile/report/benchmark-results.json
/tmp/chzzk-rust-env/bin/python experiments/rust-profile/io/bench.py --full --output experiments/rust-profile/io/results.json
/tmp/chzzk-rust-env/bin/python experiments/rust-profile/watch/watch.py matrix /tmp/chzzk-profile-watch-target/release/watch-profile --output experiments/rust-profile/watch/results.json
```

GUI 측정은 `profile_python.py --video <녹화 TS> --native-preview <실험 실행기> --output <JSON>`,
대기 프로세스는 `idle.py --seconds 8 --output <JSON>`으로 실행한다.
`native_preview.rs`는 `rustc -O`로 빌드한다. GUI에는 Qt offscreen 환경이 필요하다.
측정은 서로 순서대로 실행했고 메모리 추적은 시간 계측과 별도 패스로 분리했다.

RSS에는 단위를 붙였다. 보고서는 worker 자체 `/proc/self/status`의 VmHWM,
감시는 `/proc`의 표본 RSS, 기존 연결 코드의 RSS는 Python 실행 전체 high-water다.
`wait4.ru_maxrss`에는 부모에서 상속된 high-water가 섞이는 관측이 있어 비교에서 제외했다.
Linux CPU 합산은 중간 프로세스들이 자식을 wait하는 경우 손자까지 포함한다.
[공식 getrusage 문서](https://man7.org/linux/man-pages/man2/getrusage.2.html)

이번 결과는 한 Linux PC의 warm-cache/합성 부하 및 보존된 실녹화 표본에 대한 결과다.
전체 기능을 Rust로 포팅한 앱이나 전체 녹화 CPU/RSS 개선을 측정한 결과가 아니다.
