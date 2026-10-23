# 전체 검토 후 개선

확인: 2026-10-23, 한국 시간. 사용자는 [전체 검토](2026-10-23-repository-review.md)의 개선을 수행하고 새 브랜치에 커밋·푸시하도록 요청했다. 시작 기준은 main `5e59cd5`, 작업 브랜치는 `codex/review-improvements`다. 작업 전 변경은 직전 검토에서 작성한 미추적 보고서 한 파일이었다.

## 변경과 결정

- `chzzk_record.py:DohResolver`, `install_internal_dns_resolver()`, `main()`, `manage_recording_tasks()`: uvloop를 유지하면서 방송 API용 aiohttp connector가 기존 socket DoH 경로를 스레드에서 호출하도록 연결했다. IPv4·IPv6의 숫자 주소와 포트·프로토콜을 전달하며 원래의 시스템 DNS fallback을 유지한다. DoH 비활성 또는 설치 실패는 기본 connector 경로를 사용한다.
- `dns_over_https.py:install_doh_dns()`: 표준 socket 함수의 `host`, `port`, `type` 키워드 호출도 호환되도록 인수 이름을 맞췄다. 직접 요청과 기본 asyncio·uvloop의 aiohttp 요청을 검사한다.
- `dns_over_https.py` HTTP 본문 helper: Content-Length를 읽기 전에 제한하고 chunked 누적 크기·chunk 헤더·연결 종료까지 읽는 본문에도 상한을 적용했다. 허용 상한 65,535바이트의 정상 응답은 세 방식 모두 유지한다. 새 의존성은 추가하지 않았다.
- `record_stream()`: 대기 때 최신 설정을 조회하고 새 방송 ID의 시작 전에 전역·채널의 저장 위치·형식·분할·화질·인코더·수신 옵션을 적용한다. 재조회 간격과 비활성 여부도 대기 경계에서 확인한다. 같은 방송의 자동 복구·파일 전환에 화질을 바꾸면 기존 rendition 재개 커서가 맞지 않을 수 있으므로 해당 방송에서는 기존 옵션을 유지한다. 현재 녹화 파일을 취소해 설정을 적용하지 않는다.
- `i18n.py:gui.apply_hint`: 다음 방송부터 적용하고 같은 방송의 복구 설정은 유지한다는 안내를 5개 언어로 맞췄다. DNS·로그의 녹화기 재시작 조건은 그대로다.
- 미호출 `toggle_log_enabled()`와 그 전용 `save_json_secure()`를 제거했다. CLI·GUI의 공용 ConfigStore 저장 경로는 유지한다.
- `tests/test_hls_continuity.py`: 초기화 변경·불연속·공백 복구 테스트는 마지막 이벤트가 아니라 `kind=boundary` 이벤트를 선택한다. 대기 중 설정 변경과 같은 방송 복구의 옵션·커서 보존을 한 회귀 검사로 확인한다.
- `tests/test_dns_over_https.py`: 로컬 HTTP 서버·합성 DNS·합성 소켓으로 DoH 연결, 키워드 호환·fallback, 정상 상한과 세 가지 과대 본문 수신 중 거절을 검사한다. 계정·쿠키나 실제 CHZZK 방송은 사용하지 않는다.
- 작업은 녹화기 개선과 PR/push용 자동 검사 추가로 나눠 커밋한다. 각 커밋에는 5개 언어 CHANGELOG의 대응 항목을 포함한다. 원래 감사 보고서는 수정 전 커밋의 기록으로 보존한다.

## 검증

- `/tmp/chzzk-rekoda-review-env312/bin/python -m unittest discover -s tests -v`: Python 3.12.15, **134개 통과**, 실패·오류·건너뜀 없음, 83.711초. 기존 실제 FFmpeg 복구·파일 전환·정상 중지·파이프 지연·취소 검사도 포함한다.
- Python 3.14.8의 추가 DoH 검사 6개와 녹화 설정 검사 1개도 통과했다. uvloop와 기본 asyncio 모두 합성 DNS 이름을 실제 로컬 HTTP 서버로 연결했다.
- 수정 전 12회 중 3회 오류였던 초기화 변경 경계 검사를 Python 3.12에서 다시 12회 반복해 실패·오류 0을 확인했다. 서식 정리 후 DoH 검사 6개도 재통과했다.
- 수정 Python의 `py_compile` 통과. bytecode는 `/tmp`로 분리했다.
- 5개 언어 480개 번역 키와 서식 인수 대응 검사 통과. 사용자에게 보이는 새 적용 시점 안내는 5개 언어를 함께 수정했다.
- `git diff --check` 통과. 계정·인증 정보·개인 설정을 변경하거나 커밋하지 않는다.

## 미검증 범위

실제 CHZZK 장시간·해외 녹화, NAVER 계정 로그인, Windows/macOS 네이티브 실행, GPU 인코더는 검증하지 않았다. GUI 안내 문자열 변경의 화면 배치는 이번에 다시 렌더링하지 않았다. 실제 복구·정상 중지의 증거와 모의 DNS·설정 검사 결과를 실방송 검증으로 일반화하지 않는다.
