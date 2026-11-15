# Rust 2차 검증 검토안

- 확인일: 2026-11-15 (Asia/Seoul).
- 상태: 사용자 제안에 대한 검토안. 제품 구현·자동 복구/차단 변경은 승인 또는 완료한 것으로 취급하지 않는다.
- 제안: Python의 CDN/LL-HLS/버퍼/복구/파일 분할·종료 처리를 Rust가 추가 검증할 가치가 있다. 우선 관찰과 불일치 증거 수집으로 시작한다. 속도 향상과 무누락 보장은 별도 검증 대상이다.

## 코드 근거와 검증 대상

| 대상 | 현재 근거 | Rust에서 추가 확인할 내용 |
|---|---|---|
| CDN 선택/대체 | `plugin/chzzk.py:source_paths`, `hls_continuity.py:matches`, `prepare_standby`, `download` | 같은 방송·화질·시각 구간과 초기화 호환성 확인. 후보를 발견한 상태, 검증된 상태, 실제 출력에 사용한 상태를 구별한다. CDN 사이의 순번/URL/전체 바이트가 같다는 가정은 하지 않는다. |
| LL-HLS/미디어 | `validate_media`, `part_bytes`, `download_parts`, 실험 `experiments/rust-media-validator/src/lib.rs` | TS/MP4 구조와 잘림, 부분 조각 누락·중복·결합, 컨테이너에서 확인할 수 있는 시간·트랙 일관성을 검증한다. 실험 구현은 TS sync/길이와 최상위 MP4 box 범위·종류 검사이며 디코더나 완전한 미디어 의미 검증기가 아니다. |
| 버퍼/복구/출력 순서 | `recording_buffer.py:MediaBuffer`, `hls_continuity.py:_deliver`, `recording_continuity.py:RecordingContinuity` | 보관 파일의 크기·digest·방송 소유 정보, 출력 구간과 재개 위치, 중복 출력과 미해결 구간, 출력 완료 이전 삭제 여부를 별도로 확인한다. 정상적인 새 방송/초기화/불연속 경계에서는 비교 상태를 갱신한다. |
| 파일 분할/종료 | `chzzk_record.py:RecordingStopControl`, `hls_continuity.py:deliver/_deliver`, FFmpeg 정리 경로 | 마지막 출력 구간과 다음 파일의 시작 구간, 자식 종료·파이프 배출·footer/오류 증거를 대조한다. 닫힌 실제 파일의 probe/디코딩도 검사한다. |

`checkpoint`는 미디어를 Streamlink RingBuffer에 쓴 뒤 기록된다. FFmpeg가 최종 파일을
정상 저장했다는 독립 증거는 아니므로, 기존 이벤트를 다시 요약하는 것만으로 파일
무결성까지 검증했다고 표시하지 않는다. Python이 계산한 결론뿐 아니라 필요한 원본
바이트/파일/관측 자료를 확보해야 한다.

## 단계와 제약

1. 기존 수신 데이터를 재사용해 추가 다운로드 없이 Python/Rust 결과와 불변식 차이를 기록한다. 미디어 bytes 전달은 기존 실험 binding 또는 보관 payload 재사용의 비용·수명 계약을 먼저 비교한다. 현행 64KiB 입력 JSONL에 원시 영상을 base64로 넣는 방식은 적합하지 않다.
2. Rust 검증 대기열과 보관량에 상한을 둔다. 처리 지연·중단·검증 자료 손실은 `검증 불가`로 집계하며 통과로 처리하지 않는다. 관찰 단계의 검증기가 정상 녹화를 중단시키지 않도록 한다.
3. 잘림·조각 제거·중복·잘못된 후보·초기화 교체·타임라인 reset·버퍼 변경·분할/종료 장애를 합성 입력에 주입해 검출과 오탐을 확인한다. 동일 검증 로직을 두 언어로 옮겨 얻은 일치만으로 독립적인 정확성을 주장하지 않는다.
4. 기존 Python 검사와 별도로 저장 파일의 probe 및 FFmpeg 디코딩으로 확인한다. 추가 CPU/RSS/복사·I/O 비용과 지연도 측정한다.
5. 장시간 비교에서 효용과 오탐 범위를 확인한 뒤 명확한 손상 판정부터 조각 거절/기존 복구 경로와 연결할지 결정한다. Rust에 별도 다운로드·파일 정리 제어권을 동시에 주지 않는다.

우선순위는 미디어 구조·출력 구간 검증, 버퍼/CDN 대체 검증, 닫힌 분할 파일과 종료
증거 검증이다. 현재 Rust 보고서 분석기는 이 확장의 일부 자료를 재사용할 수 있지만,
실시간 원본 미디어/버퍼/프로세스 생명주기 감시는 아직 구현하지 않았다.

## 외부 확인 자료

- [RFC 8216 §4.3.2.3](https://datatracker.ietf.org/doc/html/rfc8216#section-4.3.2.3): 불연속 경계에서 파일 형식·트랙·timestamp sequence 변경을 구별해야 한다.
- [FFmpeg streamcopy 설명](https://ffmpeg.org/ffmpeg.html#Streamcopy): streamcopy는 디코딩을 수행하지 않으므로 저장/복사 성공과 디코딩 검증을 구별한다.
