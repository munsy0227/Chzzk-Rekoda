# Rust 부분 도입 검토

확인: 2026-11-15 (Asia/Seoul), `main` / `797820e`.
상태: **초기 검토 후 시험 구현 완료**. 사용자가 2026-11-15에 테스트를 지시해
`experiments/rust-media-validator/`에서 PyO3 비교·회귀 검사를 수행했다.
제품 경로 연결과 배포 변경은 하지 않았다. 결과는
[작업 기록](../worklogs/2026-11-15-rust-adoption-review.md)의 후속 실험 절을 따른다.

## 권고

성능 개선을 목적으로 한 제품 도입은 프로파일링 결과가 나온 뒤 결정한다.
Rust를 시험하려면 `hls_continuity.py:validate_media()` 하나를 대상으로 한다.
작은 독립 함수여서 비교 검증하기 좋다는 뜻이며, 현재 병목으로 확인됐다는 뜻은 아니다.
GUI·설정·인증·HLS 복구 전체를 첫 전환 대상으로 삼을 근거는 부족하다.

## 현재 구조와 후보

| 대상 | 실제 처리 | 도입 판단 |
| --- | --- | --- |
| `hls_continuity.py:validate_media` | TS 동기 바이트 및 ISO-BMFF 최상위 박스 경계·필수 박스 검사 | 작은 시험 구현의 첫 후보. TS는 188바이트마다 Python 반복문을 실행하지만 fMP4는 본문을 건너뛰므로 전체 성능 이득은 불확실하다. 디코더가 아니며 정상 영상 전체를 보증하지 않는다. |
| `recording_buffer.py:MediaBuffer` | 파일 저장·교체·재로드, SHA-256, 잠금 및 시간·용량 예약 | 우선순위 낮음. 해시는 이미 네이티브 구현이며 디스크 대기는 언어 변경만으로 사라지지 않는다. 메모리 복사와 잠금 경합은 별도 측정 대상이다. |
| `hls_continuity.py`의 worker/writer/reader 및 `plugin/chzzk.py` | Streamlink 상속, HTTP 요청, LL-HLS, 재시도·전환·중지·출력 순서 | 첫 도입 보류. Streamlink 객체와 스레드·future·상태 전이가 깊게 연결된다. Rust의 타입·소유권만으로 시간 순서 및 복구 정책의 정확성이 확보되지는 않는다. |
| `chzzk_record.py` 녹화 관리 및 파이프 | asyncio 제어, 자식 프로세스, Streamlink 출력→FFmpeg 입력 전달 | 병목 증거 없이 전환할 이유가 약하다. 인코딩은 이미 FFmpeg가 담당하며, 작은 함수 이식으로 Python 프로세스 자체를 제거할 수는 없다. |
| `continuity_report.py:summarize` | NDJSON 검증, 시각 비교, 구간 병합 및 판정 | 녹화 경로 밖의 학습 실험 대안. 보고서 처리가 실제로 느린지는 미측정이며, 녹화 CPU·끊김 개선을 기대하는 대상으로는 부적합하다. |
| PySide6 GUI·설정·로그인·`recorder_bridge.py`·`process_utils.py` | 사용자 설정, Python 공유 상태 및 OS별 파이프·프로세스 처리 | 유지 권고. 이식 범위에 비해 성능상 이득 근거가 부족하고 플랫폼 호환성을 다시 검증해야 한다. |

근거: `validate_media` 202–229행, 호출 291/292/1161/1212/1362/1389행;
`MediaBuffer.store/load` 129–178행; HLS Streamlink 상속 및 스레드 풀 699/835행 이후;
`chzzk_record.py:pipe_stream_to_stdin` 821행 이후 및 FFmpeg 실행부;
`continuity_report.py:summarize` 60–166행.

`pyproject.toml`에는 이미 Rust 기반 JSON 라이브러리인 `orjson`이 있다.
직접 관리하는 Cargo 프로젝트와 Rust 빌드 설정은 현재 없다.
기본 회귀 CI는 Ubuntu에서 Python unittest를 실행한다. 실방송 수동 워크플로에는
Linux/Windows/macOS 선택이 있지만 Rust 빌드·wheel 설치 검증은 없다.
README의 Android 설치 튜토리얼 링크를 Android/Termux CI 검증으로 해석하지 않는다.

## 연결 방식

작은 런타임 함수가 유효한 대상으로 확인되면 **PyO3 + maturin 확장 모듈**이 맞는다.
현재 `validate_media(data, is_map=False)` 호출부와 `Unavailable(category="invalid_media")`
예외 계약은 Python에서 유지하고 내부 검사만 Rust에 맡긴다.
미디어 조각마다 별도 실행파일을 시작하거나, 조각 전체를 JSON/IPC로 왕복시키지 않는다.
초기 성능 비교에는 Python↔Rust 호출과 입력 전달·복사 비용까지 포함한다.

별도 Rust 실행파일은 오프라인 보고서 분석처럼 파일 입력→JSON 결과로 끝나는 작업에는
가능하다. 녹화 worker를 독립 실행파일로 교체하면 HTTP·인증·복구·정상 중지·이벤트
프로토콜까지 책임져야 하므로 작은 함수 이식과는 다른 규모의 작업이다.

제품 배포 전에는 타깃별 wheel 빌드·설치, `uv` 설치 경로, Rust 의존성 잠금,
Linux libc 호환성과 Windows/macOS 실행 검증이 필요하다. `abi3` 사용 가능성을
검토할 수 있지만 OS·CPU별 빌드가 없어지는 것은 아니다. 사용자 설치 시 컴파일을
요구할지, 사전 빌드 wheel을 제공할지도 정해야 한다.
미지원 환경에서 기존 Python을 유지한다면 모듈 부재 시에만 대체하며, 검증 실패를
성공으로 바꾸는 예외 처리는 넣지 않는다. 두 구현을 유지하는 비용도 도입 비용에 포함한다.

## 최소 실험과 판정 기준

1. 대표 녹화에서 관리자·Streamlink 자식·FFmpeg를 구분해 CPU·RSS·입출력 대기를 측정한다.
   기본 복사 녹화와 재인코딩, 실제 사용하는 채널 수, 정상 수신과 복구 상태를 구분한다.
   작은 함수의 실행 시간만으로 전체 녹화 성능을 추정하지 않는다.
2. 실험 브랜치에서 `validate_media`만 구현한다. 초기 비교는 합성 TS/fMP4·init·LL-HLS
   조각으로 수행하며 제품 설치 경로에 Rust를 필수로 넣지 않는다.
3. 기존 Python을 비교 기준으로 같은 입력의 허용/거부 결과와 오류 분류를 맞춘다.
   기존 `tests/test_hls_continuity.py:test_rejects_truncated_containers`와 실제 미디어·부분
   조각 검사를 재사용한다. 정상 TS와 sync 손상/188바이트 미정렬, 빈 입력,
   MP4 일반·확장·0 크기, 짧은 헤더, 범위 초과, 필수 박스 누락, `is_map` 차이를 확인한다.
   구조에 맞는 입력과 의도적으로 손상시킨 입력을 생성하고 판정 동등성을 검사한다.
   기존 구현의 명백한 오류를 발견하면 호환성 유지와 별도 오류 수정을 구분한다.
4. 새 속성 기반 테스트 라이브러리는 자동 추가하지 않는다. 현재 unittest와 생성 사례로
   시작하고, Hypothesis/proptest가 필요하면 검증할 규칙과 의존성을 먼저 제안한다.
5. release 빌드에서 호출·입력 전달 비용을 포함해 비교하고 전체 녹화의 CPU/RSS와
   연속성·중지 동작을 다시 확인한다. 기존 전체 unittest 및 OS별 설치/녹화 검증을 수행한다.
6. 허용/거부 동등성과 실제 부하 감소가 확인되고 배포 비용을 감당할 때 제품에 반영한다.
   함수만 빨라지고 전체 녹화 부하가 유의미하게 달라지지 않으면 Python 구현을 유지한다.

## 공식 자료

- [orjson 프로젝트 메타데이터](https://github.com/ijl/orjson/blob/master/pyproject.toml)
- [Python 3.12 hashlib: 네이티브 해시와 GIL 해제](https://docs.python.org/3.12/library/hashlib.html)
- [PyO3 성능: 변환·호출·인터프리터 접근 비용](https://pyo3.rs/main/performance.html)
- [PyO3 빌드·배포 및 ABI](https://pyo3.rs/main/building-and-distribution.html)
- [maturin 배포·Linux 호환성·크로스 컴파일](https://www.maturin.rs/distribution)

## 이번 검토의 한계

초기 검토는 소스·기존 테스트·CI·설치 경로와 공식 문서 확인이었다.
이후 사용자 지시로 함수 비교·성능 측정·기존 회귀 검사를 완료했다.
실방송 및 타 OS/Android 설치 검증은 수행하지 않았다.
함수의 속도 향상을 전체 녹화 성능 개선이나 녹화 누락 감소로 일반화하지 않는다.

## 후속 제안: 대기 채널의 방송 감시를 Rust로 분리

2026-11-15 사용자 질문: 방송 상태 확인 등을 Rust로 만들고 녹화는 기존 방식대로
유지하는 방안. **검토 제안이며 구현 합의·구현 완료가 아니다.**

책임 경계가 분명한 시험 대상으로 볼 수 있다. 첫 범위는 녹화 대기 채널의 API 상태
조회·조회 간격·실패 재시도로 한정한다. Rust 감시기는 상태 관측을 전달하고,
기존 Python은 녹화 세션의 유일한 관리자 역할을 유지한다.

- Python: 기존 공용 설정·채널 활성화·인증·CLI/GUI·녹화 시작 최종 확인,
  Streamlink/FFmpeg 실행과 복구·파일 전환·정상 중지를 담당한다.
- Rust: Python이 전달한 대기 채널 목록과 조회 주기로 감시하고, 버전 있는 NDJSON으로
  채널 ID·방송 ID·상태·조회 시각·오류 분류를 반환한다. 매 조회마다 새 프로세스를
  띄우지 않고 오래 실행되는 감시기 하나를 사용한다. 별도 서버/DB는 필요 없다.
- 감시기가 설정 파일·쿠키를 직접 소유하거나 수정하지 않는다. 처음에는 공개 상태를
  시작 후보 알림으로 쓰고 기존 Python의 인증된 최종 조회를 유지한다. 회원/연령/접근
  제한 정책을 단순 OPEN 상태로 대체하지 않는다.
- `(channel_id, live_id)`로 같은 방송의 중복 시작을 막고 오래된 관측을 구분한다.
  HTTP 실패·타임아웃·차단은 방송 종료와 구분한다. 조회 주기와 동시 요청 수는 기존
  수준을 유지하고, 언어 변경을 이유로 API 요청량을 늘리지 않는다.
- Rust의 CLOSE 관측이나 감시기 장애만으로 진행 중인 녹화를 종료하지 않는다.
  마지막 미디어 배출·완료 checkpoint·정상 중지·90초 복구 기한 등은 기존 녹화기에
  남긴다. 녹화 중인 채널은 감시기에서 제외하거나 대기 감시와 중복 조회하지 않는다.
- 설정 변경·감시기 종료/재시작·부모 종료 시 수명 관리는 필요하다. 장애 시 기존
  Python 감시로 대체할 경우 감시 주체는 한쪽만 활성화한다.

현재 `chzzk_record.py:get_live_info`(1102행 이후)는 aiohttp 비동기 조회와 회원 접근
검사를 수행한다. `record_stream`(2296/2329행)은 대기 중 조회와 화질 조회 실패 후
재확인에 사용하며, `manage_recording_tasks`(3152행 이후)가 하나의 ClientSession을
공유한다. `timeout` 설정은 다음 조회까지 기다리는 간격으로도 쓰인다. 따라서
언어 변경만으로 네트워크 대기나 조회 간격이 줄어드는 것은 아니다.

Rust 구현에서도 공유 비동기 HTTP 클라이언트를 재사용할 수 있다.
[reqwest Client 공식 문서](https://docs.rs/reqwest/latest/reqwest/struct.Client.html)는
연결 풀을 가지므로 Client 하나를 재사용하도록 안내한다. 이는 가능한 구현 수단이며
현재 의존성 추가 결정을 뜻하지 않는다.

효과는 미측정이다. 몇 개 채널을 감시하는 데스크톱 사용에서는 이득이 작을 수 있고,
GUI/Python 관리자도 계속 실행하면 Rust 프로세스 추가로 총 RSS가 늘 수도 있다.
녹화하지 않을 때 Python 녹화 관리자를 아예 실행하지 않는 headless 구조는 별도
확장 단계다. 실제 배포 전에는 같은 채널 수·조회 주기에서 대기 CPU/RSS·시작 감지
지연·API 요청 수를 비교하고 중복 시작·상태 오판·감시기 재시작을 검증해야 한다.

## 추가 모듈 검토

2026-11-15 사용자가 방송 감시 이외의 Rust 후보도 확인하도록 요청했다.
아래 순위는 분리하기 좋은 경계와 변경 비용을 기준으로 하며 새 성능 측정 결과가 아니다.
이번 요청에서는 구현·의존성 변경·새 기능 추가를 하지 않았다.

### 우선 검토 가능한 별도 도구: 연속성 보고서 분석

`continuity_report.py:summarize`(60–166행)는 NDJSON 입력을 받아 공백·중복·미해결·오류와
최종 JSON 판정을 반환한다. CLI의 파일 입력/출력 경계(169–187행)가 이미 있고,
`scripts/run_recording_test.py:save_summary` 및 기존 HLS/중지 테스트가 호출한다.
녹화 바이트 전달과 분리돼 있어 Rust 독립 실행파일로 실험하기 가장 쉽다.

대형 보고서에서 JSON 파싱·시간 비교·구간 병합의 비용이 확인될 때 우선 검토한다.
작은 보고서의 처리 시간은 측정하지 않았고, 녹화 처리량 개선 대상도 아니다.
현재 JSON을 읽은 뒤 다시 직렬화하고 `parse_event`에서 재파싱하는 경로도 있으므로,
Rust 도입 전 기존 의존성·중복 처리 감소를 비교할 여지가 있다.

이식한다면 기존 Python 결과를 비교 기준으로 사용하고 완료 footer·버전·행 제한·
20ms 공백/중복 경계·시간대·출력 반올림·`passed` 실패 조건을 보존한다.
보고서 생성은 Python에 두고 분석만 옮겨 시작한다. 독립 도구의 JSON 결과를 기존 Python
CLI에서 표시하면 5개 언어 출력 체계도 유지할 수 있다. 입력 거부·실패를 성공으로 바꾸는
회귀는 녹화 파일을 손상시키지 않아도 CI 판정을 잘못 통과시킬 수 있으므로 비교 검증이 필요하다.

### 부하 측정 후 판단할 경로

- `recording_buffer.py:MediaBuffer.store/load`(129–178행): 큰 바이트의 결합·읽기·분할은
  메모리 복사 후보지만 해시는 이미 hashlib이고 저장·잠금·교체 비용은 남는다.
  `sha256(initialization + media)`의 결합 복사부터 Python `update` 두 번으로 줄이는
  작은 대안을 비교할 수 있다. Rust가 필요하다면 바이트 처리에 국한하고 방송/화질 귀속,
  시간·용량·개수 제한과 디스크 실패·정리 계약은 그대로 유지해야 한다.
- `BufferedDownload.materialize`(hls 288행 이후): `buffered_download`(907–919행)의
  후보 검사와 `_deliver`(1665행 이후)의 출력 직전 검사에서 파일 읽기·해시·검증을
  반복하는 경로가 있다. 선행 검사는 복구 시작 후보 선택(1078행)에도 쓰이므로 단순히
  삭제해도 안전하다고 판단하지 않는다. 실제 복구 부하를 측정해 중복 작업을 줄일 수 있는지
  검토할 Python 개선 후보이며 Rust 이식을 정당화하는 측정은 아니다.
- `chzzk_record.py:pipe_stream_to_stdin`(821–842행): 256KiB 단위 중계와 역압력 처리가
  다채널에서 CPU/복사 병목으로 확인될 때만 검토한다. Rust 중계 프로세스 추가가 자동으로
  복사를 없애지는 않는다. OS 파이프 연결 방식부터 검토할 수 있지만 EOF·배출·정상 종료·
  Windows 파이프 계약까지 영향이 있어 현재 녹화 경로를 보존하려는 방향에서는 후순위다.
- `recording_output_size`(1470–1485행): 분할 파일 목록을 정렬하고 모든 파일을 stat하는
  경로가 `read_stream`(1557행 부근)에서 반복 호출된다. Rust로 같은 목록/시스템 호출을
  반복하기보다 닫힌 파일 크기의 재조회·정렬을 줄일 여지가 먼저다. 이름 변경·삭제·빈 새
  파일이 있을 때의 정확성은 유지해야 한다. GUI 미리보기 파일 선택도 같은 목록 함수를 쓴다.

### 유지할 부분

`gui/services.py:Images/Preview`는 Qt 네트워크·이미지 객체·QProcess와 FFmpeg를 연결한다.
인코딩과 미리보기 디코딩을 Rust로 감싸도 FFmpeg가 하는 작업은 남는다.
`process_lock.py`는 작은 OS 잠금 어댑터이며 `process_utils.py`는 특히 Windows overlapped
파이프 계약에 묶여 있다. 설정 저장은 임시 파일·fsync·replace·revision 충돌 처리,
로그인은 Selenium/쿠키 처리와 결합돼 있어 속도상 필요가 확인되지 않은 이식은 권하지 않는다.
DoH도 Python socket 패치·aiohttp resolver·Streamlink sitecustomize에 걸쳐 있어 별도
Rust 도구로 옮기면 기존 Python 소비자와의 연동이 추가로 필요하다.

Rust 감시기에 녹화 프로세스 감독까지 붙이는 것은 가능한 후속 설계지만 현재
`record_stream`이 대기·복구·종료를 함께 소유하며 프로젝트 잠금도 recorder 하나를 전제한다.
채널별 Python 녹화기를 여러 개 띄우는 방식으로 단순 확장할 수 있다고 가정하지 않는다.
해당 구조 변경을 별도 목표로 정하기 전에는 Python의 세션 소유권을 유지한다.

공식 확인 근거: [hashlib의 OpenSSL/HACL 구현과 GIL 해제](https://docs.python.org/3.12/library/hashlib.html),
[Qt QProcess](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html),
[asyncio 전송 API](https://docs.python.org/3.12/library/asyncio-eventloop.html#asyncio.loop.sendfile).
특히 sendfile API는 일반 파일 입력을 요구하므로 현재 파이프→파이프 중계를 그대로
치환할 수 있다고 제안하지 않는다.

## 전체 측정 완료

2026-11-15 사용자가 "그냥 다 측정해보자"라고 지시해 방송 감시·보고서 분석·
해시/버퍼·파이프·파일 집계 및 기존 Qt/DNS/설정/OS 연결 코드를 측정했다.
비교 코드는 `experiments/rust-profile/`에 있고 제품에는 연결하지 않았다.
방법·원시 반복값·범위 제한은 [전체 측정 결과](../../experiments/rust-profile/README.md)를 따른다.

측정 후 우선순위는 독립 감시기의 자원 절감 가능성, 큰 보고서 분석의 속도 개선,
그 밖의 경로에서는 기존 Python의 복사·재조회·중계 구조 개선 순이다.
기존 Python/GUI가 상주하면 Rust 감시기의 RSS를 그대로 절약한다고 볼 수 없고,
보고서 Rust 시험 구현은 큰 입력을 통째로 읽어 Python보다 RSS가 커지기도 했다.
파이프의 빠른 대량 전달 결과를 실제 네트워크 입력 녹화의 개선 배수로 쓰지 않는다.
제품 도입·추가 API 요청·설정/로그인 이식은 수행하지 않았다.

## 기능 브랜치 구현

이후 사용자의 기능 브랜치 구현 지시에 따라 `codex/rust-features`에서
`native/`와 `native_backend.py`를 제품 경로에 연결했다. 실험 디렉터리를 직접
import하지 않고 방송 상태 HTTP 조회와 큰 연속성 보고서만 선택형 실행 파일로
처리한다. 녹화·복구·설정·로그인과 DoH는 기존 방식이며 실행 파일이 없거나
입력을 확실히 처리하지 못하면 Python으로 대체한다.
구현·검증 및 남은 범위는 [기능 작업 기록](../worklogs/2026-11-15-rust-features.md)을 따른다.
