# 저장소 전체 검토

확인일: 2026-10-23, 한국 시간. 검토 기준 커밋: `5e59cd5`.
사용자 요청: Ponytail full 모드에서 저장소를 전체적으로 검토한다.

이 저장소는 CHZZK 방송을 확인하고 Streamlink로 받은 영상을 FFmpeg로 저장하는 자동 녹화 프로그램이다. CLI와 Qt GUI가 설정과 녹화 엔진을 공유한다. 한 사용자가 한 프로젝트에서 몇 개 채널을 동시에 녹화하는 데스크톱 사용을 기준으로 검토했으며, 대규모 채널 부하 시험은 하지 않았다.

실행 코드, 설정, 기존 테스트, 의존성, 실행기, 두 Actions 워크플로와 관련 설계·작업 기록을 검토했다. 아래는 재현 또는 구체적인 실행 경로를 확인한 항목이다. 실행 코드 수정, 커밋, 원격 작업은 하지 않았고 이 보고서만 추가했다.

## 우선 수정 — Must fix

### 1. [P2] uvloop에서 방송 API 조회가 DoH 설정을 우회한다

- **대상:** [녹화기 uvloop 설정](/home/munsy0227/Chzzk-Rekoda/chzzk_record.py:3428), [aiohttp 세션 생성](/home/munsy0227/Chzzk-Rekoda/chzzk_record.py:3142), [DNS 설치](/home/munsy0227/Chzzk-Rekoda/dns_over_https.py:324).
- **역할:** DoH는 DNS 요청을 HTTPS로 보내는 기능이다. 녹화기는 방송 상태를 aiohttp로 먼저 조회하고, 방송 중이면 Streamlink를 시작한다.
- **문제:** DoH 설치는 Python의 `socket.getaddrinfo`만 교체하지만, Unix 진입점에서 사용하는 uvloop의 주소 조회는 이 함수를 통과하지 않는다. 시스템 DNS가 CHZZK 주소를 해석하지 못하고 DoH는 해석할 수 있는 환경에서도, 선행 방송 조회가 실패해 녹화를 시작하지 못한다.
- **최소 수정:** 방송 조회용 aiohttp connector에 기존 DoH 해석기를 실제로 사용하는 resolver를 명시적으로 연결한다. uvloop에서의 aiohttp 조회까지 확인하는 작은 회귀 검사를 남긴다.
- **미수정 영향:** DoH 사용 안내가 출력되어도 녹화 시작에 필요한 API 조회는 시스템 DNS에 의존한다. Streamlink 자식에 전달되는 DoH 설정만으로는 이 경로를 보완하지 못한다.

**재현:** 네트워크 요청 대신 `DnsOverHttpsResolver.resolve()`가 합성 주소 `127.0.0.123`을 반환하도록 대체하고, 같은 합성 호스트를 조회했다. 설치 환경에서 다음 결과를 확인했다.

| 조회 경로 | 결과 | DoH 해석기 호출 |
| --- | --- | --- |
| `socket.getaddrinfo`, 위치 인수 사용 | `127.0.0.123` | 있음 |
| 기본 asyncio `loop.getaddrinfo` | `127.0.0.123` | 1회 |
| uvloop `loop.getaddrinfo` | `gaierror` | 0회 |
| uvloop의 `aiohttp.ThreadedResolver` | `gaierror` | 0회 |

실제 외부 DoH 서비스의 장애나 차단 상태를 주장하는 결과가 아니다. 현재 설치된 라이브러리와 녹화기의 이벤트 루프 조합에서 발생하는 연결 누락을 검증했다. macOS에서도 uvloop를 선택하는 코드지만 직접 재현한 OS는 Linux다.

### 2. [P2] 저장한 녹화 옵션이 대기 중인 채널의 다음 녹화에 반영되지 않는다

- **대상:** [채널 작업 재사용](/home/munsy0227/Chzzk-Rekoda/chzzk_record.py:3189), [시작 시 옵션 고정](/home/munsy0227/Chzzk-Rekoda/chzzk_record.py:2250), [화질 조회](/home/munsy0227/Chzzk-Rekoda/chzzk_record.py:2300), [설정 화면 안내](/home/munsy0227/Chzzk-Rekoda/gui/settings_dialog.py:96).
- **역할:** 관리자는 설정을 주기적으로 다시 읽고 채널마다 장기간 유지되는 `record_stream()` 작업을 실행한다. 설정 화면은 저장한 녹화 옵션이 다음 녹화 작업부터 적용된다고 안내한다.
- **문제:** 기존 채널 작업에는 변경된 설정을 전달하지 않고, 작업 안에서는 최초 화질·저장 위치·형식·분할·인코더 설정을 계속 사용한다. 방송 전 대기 상태에서 변경해도 다음 방송이 시작될 때 과거 옵션으로 녹화하며, 다시 읽는 과거 1시간 옵션과 쿠키는 예외다.
- **최소 수정:** 현재 파일의 녹화와 정리는 유지하면서, 다음 녹화 시도를 시작하기 전에 최신 전역·채널 설정을 다시 읽어 유효 옵션을 계산한다. 대기 중 설정 변경 후 방송이 시작되는 경로를 검사한다.
- **미수정 영향:** 사용자가 저장 폴더나 화질을 바꿨다고 생각해도 이전 폴더·화질로 녹화한다. 중지 후 재시작하거나 채널 작업을 새로 만들기 전까지 변경이 반영되지 않을 수 있다.

**재현:** 관리자가 `output_dir=old`, `output_format=ts` 작업을 시작한 뒤 설정을 `new`, `mkv`로 바꿔 두 번 읽게 했지만 작업은 한 번만 생성되고 전달 인수도 `old`, `ts`로 남았다. 실제 `record_stream()`에도 합성 `CLOSE → OPEN` 응답을 주고 최신 설정의 화질을 `720p60`으로 바꿨지만 `prepare_recording_quality()`는 최초 값 `best`를 받았다. 외부 방송과 자식 프로세스를 사용하지 않는 격리 검사다.

### 3. [P2] DoH 응답 크기 제한이 전체 다운로드 뒤에 적용된다

- **대상:** [제한 검사 위치](/home/munsy0227/Chzzk-Rekoda/dns_over_https.py:140), [HTTP 본문 읽기](/home/munsy0227/Chzzk-Rekoda/dns_over_https.py:222), [길이 지정 수신](/home/munsy0227/Chzzk-Rekoda/dns_over_https.py:362), [chunked 수신](/home/munsy0227/Chzzk-Rekoda/dns_over_https.py:374), [연결 종료까지 수신](/home/munsy0227/Chzzk-Rekoda/dns_over_https.py:413).
- **역할:** DoH 응답은 외부 서버에서 받은 데이터이며 코드에는 `MAX_DNS_MESSAGE_BYTES=65535` 제한이 있다.
- **문제:** 본문을 전부 메모리에 모은 뒤 크기를 검사하므로, 큰 `Content-Length`나 계속 이어지는 chunked·길이 미지정 응답에는 제한이 수신 중 작동하지 않는다. DoH가 활성화된 상태에서 서버가 비정상적인 대용량 응답을 보내면 메모리 사용과 대기가 커질 수 있다.
- **최소 수정:** `Content-Length`를 본문 수신 전에 검사하고, 세 가지 본문 수신 루프 모두 누적 크기가 상한을 넘기 전에 중단한다. 합성 소켓으로 각 수신 방식의 초과 응답 거절을 검사하면 된다.
- **미수정 영향:** DNS 응답 상한이 있어도 녹화 프로세스의 메모리를 보호하지 못한다. DoH 기본값은 꺼짐이며 정상적인 작은 응답만 오는 환경에서는 이 문제가 드러나지 않는다.

**재현:** 합성 HTTP 소켓에 66,559바이트 본문을 넣었다. `_read_http_response()`는 65,535바이트 상한을 넘긴 본문을 전부 받아 반환했다. 이후 `_post_dns_message()`가 거절하더라도 이미 받은 메모리와 수신 시간은 되돌리지 못한다. 실제 대용량 응답으로 메모리를 소진시키는 시험은 하지 않았다.

## 보완 필요 — Should fix

### 4. [P2] 정상 이벤트의 도착 순서 때문에 회귀 테스트가 간헐적으로 실패한다

- **대상:** [초기화 변경 테스트](/home/munsy0227/Chzzk-Rekoda/tests/test_hls_continuity.py:608), [같은 가정의 테스트](/home/munsy0227/Chzzk-Rekoda/tests/test_hls_continuity.py:563), [불연속 테스트](/home/munsy0227/Chzzk-Rekoda/tests/test_hls_continuity.py:615).
- **역할:** 초기화 데이터가 바뀌거나 불연속 지점을 만났을 때 파일 전환 이벤트와 재개 위치를 검사한다.
- **문제:** `self.events()[-1]`을 boundary로 가정하지만, 작업 스레드의 버퍼 상태 이벤트가 뒤에 붙을 수 있다. 전체 테스트에서 실제 출력 바이트 검사는 통과한 뒤 `boundary["reason"]`에서 `KeyError`가 발생했다.
- **최소 수정:** `kind == "boundary"`인 이벤트를 명시적으로 선택하고 그 이유와 재개 위치를 검사한다. 같은 마지막 이벤트 가정을 쓰는 세 테스트의 네 참조를 함께 고친다.
- **미수정 영향:** 제품의 파일 전환이 맞아도 테스트가 실패해 회귀 판정에 잡음이 생긴다. 이번 실패만으로 영상 손상이나 전환 실패가 발생했다고 판단하면 안 된다.

**재현:** 전체 127개 테스트 중 이 테스트 하나가 오류로 끝났다. 해당 테스트를 별도로 12회 반복하자 3회 같은 오류가 발생했고, 실패 시 마지막 이벤트들은 `checkpoint → recovery_snapshot → boundary(initialization_changed) → buffer_status`였다. 이 횟수를 일반적인 실패 확률로 해석하지 않는다.

### 5. [P2] 기존 회귀 테스트가 PR·push에서 자동 실행되지 않는다

- **대상:** [장시간 녹화 워크플로 트리거](/home/munsy0227/Chzzk-Rekoda/.github/workflows/long-recording-test.yml:3), [코덱 워크플로 트리거](/home/munsy0227/Chzzk-Rekoda/.github/workflows/codec-smoke-test.yml:3).
- **역할:** 저장소에는 로컬 합성 HLS·FFmpeg·중지·CI 실행기를 검증하는 127개 테스트가 있다.
- **문제:** 현재 저장소의 두 워크플로는 모두 수동 `workflow_dispatch`만 사용한다. PR에서 이 테스트들을 깨뜨려도 저장소에 정의된 워크플로가 자동으로 이를 검사하지 않는다.
- **최소 수정:** PR·push용 작은 워크플로 하나에서 잠금 의존성·FFmpeg를 준비하고 `python -m unittest discover -s tests`를 실행한다. 실제 CHZZK 방송이 필요한 장시간·코덱 검사는 기존 수동 방식으로 유지한다.
- **미수정 영향:** 현재의 테스트 자산이 수동 실행 여부에 의존하므로 회귀를 병합 전에 발견하기 어렵다. 외부 저장소 규칙이나 별도 서비스의 검사 여부는 확인하지 않았다.

## 정리 후보 — Nice to have

### 6. [P3] 사용되지 않는 로그 토글과 직접 저장 함수를 삭제할 수 있다

- **대상:** [로그 토글](/home/munsy0227/Chzzk-Rekoda/chzzk_record.py:166), [직접 JSON 저장](/home/munsy0227/Chzzk-Rekoda/chzzk_record.py:410).
- **역할:** `toggle_log_enabled()`는 설정의 로그 플래그를 뒤집고 `save_json_secure()`로 저장한다.
- **문제:** 숨김 파일을 포함한 저장소 전체 검색에서 토글을 호출하는 코드가 없고, 저장 함수의 유일한 호출자는 그 토글이다. 현재 CLI·GUI 설정 저장은 별도 공용 경로를 사용한다.
- **최소 수정:** 두 함수만 삭제한다. 함수 범위 기준 27줄이며 새 추상화나 의존성은 필요 없다.
- **미수정 영향:** 당장 실행되는 오류는 없지만, 잠금과 원자적 교체를 쓰지 않는 옛 저장 경로가 정상적인 공용 경로 옆에 남는다. 저장소 밖의 별도 사용자 스크립트에서 직접 import하는지는 확인하지 않았다.

Lean: 약 27줄 삭제 가능, 의존성 삭제 후보 0개.

## 수행한 검증

| 항목 | 현재 확인 결과 |
| --- | --- |
| 전체 unittest | 127개 실행, 126개 통과, 1개 오류. 테스트 실행 시간 76.546초. 위 4번의 이벤트 순서 오류 |
| 실패 사례 반복 | 초기화 변경 테스트 12회 중 같은 오류 3회, 나머지 9회 통과 |
| 녹화 설정 갱신 | 관리자 작업 재사용과 실제 대기 채널의 다음 화질 조회에서 이전 옵션 유지 재현 |
| uvloop·aiohttp와 DoH | 합성 해석기와 호스트로 DoH 호출 누락 재현. 외부 계정·쿠키 사용 없음 |
| DoH 응답 크기 | 합성 HTTP 응답으로 수신 단계의 상한 미적용 재현 |
| Python 문법 | 저장소 Python 파일 37개를 `compile()`로 검사, 오류 없음. bytecode 저장하지 않음 |
| Qt 설정 | offscreen에서 한국어·영어·간체·정체·일본어 설정 대화상자 생성 후 수집·정규화 값이 기본 설정과 일치 |
| 번역 | 5개 언어 각각 480개 키 일치, 서식 인수 불일치 없음, GUI의 정적 `self.t()` 키 누락 없음 |
| 비밀 파일 추적 여부 | `git ls-files`에서 config/cookie JSON, `.env`, PEM/key 이름의 추적 파일 없음. 개인 설정·쿠키 원문은 읽지 않음 |

환경은 `/tmp/chzzk-rekoda-review-env`에 `uv.lock` 기준으로 마련했다. Python 3.14.8, Streamlink 8.6.2, aiohttp 3.14.4, uvloop 0.22.1, PySide6 6.11.2, 시스템 FFmpeg n9.0.2를 사용했다. 테스트는 로컬 HTTP·합성 미디어 및 실제 FFmpeg를 사용하는 기존 통합 검사도 포함하지만 실제 CHZZK 장시간 녹화 결과를 대신하지 않는다.

전체 테스트 재실행 명령:

```sh
uv run --locked python -m unittest discover -s tests -v
```

초기화 변경 사례만 실행하는 명령:

```sh
uv run --locked python -m unittest discover -s tests -p test_hls_continuity.py -k test_map_change_emits_resume_boundary -v
```

## 판단과 미검증 범위

**판단:** 먼저 1번 DoH 연결과 2번 다음 녹화의 설정 갱신을 수정하고, 3번 외부 응답의 수신 상한과 4번 테스트의 이벤트 선택을 보완하는 것이 좋다. 현재의 복구·파일 보존·정상 중지 보호 장치와 다국어 설정의 기본 구조는 유지할 가치가 있다.

**미검증:** 실제 CHZZK 장시간·해외 녹화, NAVER 계정 로그인, Windows/macOS 네이티브 동작, GPU 인코더, 실제 화면 조작·한글 입력·DPI·트레이, 다수 채널의 성능 부하는 확인하지 않았다. i18n 전체 문장의 번역 품질, 모든 언어 README의 문장 단위 대응, 외부 서비스의 현재 운영 정책도 검토 범위에 포함하지 않았다.

남은 작업은 위 항목의 수정이다. 이번 요청은 검토이므로 제품 코드와 기존 테스트는 변경하지 않았다.
