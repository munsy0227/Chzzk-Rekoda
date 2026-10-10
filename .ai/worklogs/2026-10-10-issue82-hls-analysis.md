# 이슈 #82 HLS 영상 누락 분석

이 문서 앞부분은 최초 분석 당시의 기록이다. 사용자 승인 이후의 구현·추가 채널 조회·검증 결과는 뒤의 **구현 승인 후 결과**에 이어 기록한다.

- 확인일: 2026-10-10 (Asia/Seoul).
- 사용자 요청: 이슈 #82를 해결하기 위한 사전 분석. 사용자가 열어 둔 치지직 방송 페이지의 소스와 현재 녹화 코드를 대조한다.
- 시작 상태: `main`, `9fb880e`, 작업 트리 깨끗함. 런타임 코드는 수정하지 않았고 커밋/push/이슈 댓글 작성도 하지 않았다.
- 읽은 지침: `.ai/AGENTS.md`, `.ai/codex.md`, `.ai/KNOWLEDGE.md`; 관련 기록은 `2026-10-08-streamlink-urllib3-compatibility.md`.

## 이슈에서 확인한 사실

- [이슈 #82](https://github.com/munsy0227/Chzzk-Rekoda/issues/82)는 TS 길이 약 4시간 43분, 변환 후 약 2시간 48분, 재생 중 장면 점프, 파일 전환 시 구간 누락을 보고한다.
- [로그 댓글](https://github.com/munsy0227/Chzzk-Rekoda/issues/82#issuecomment-6078492114)의 첫 사례는 Streamlink `Read timeout, exiting`, Streamlink 반환 코드 1, FFmpeg 반환 코드 0이다. 실제 경과 34분 34초에 출력 시간은 24분 20초, 프레임은 87,000개다. 출력 진행 지연은 확인되지만 이 수치만으로 누락량을 확정하지 않는다.
- 같은 댓글의 두 번째 사례는 FFmpeg `No space left on device`, 반환 코드 228이며 `.ts.part` 보존은 이 실패 처리 결과다. 두 사례를 저장 공간 부족 하나로 설명하면 안 된다.
- [신고자 댓글](https://github.com/munsy0227/Chzzk-Rekoda/issues/82#issuecomment-6082766479)은 인코딩 기능을 사용하지 않았다고 명시한다. 로그에서도 영상·음성 stream copy가 확인된다.
- 사용자가 올린 플러그인 SHA-256 `e91bfbb71f39dbf4d94f501b469d8d84d10817b89b4849a7e14d5c408168b470`은 현재 `plugin/chzzk.py`와 같다.
- 글로벌 CDN으로 해결된다는 댓글은 추가 실험 근거가 없고 이번 분석으로 검증되지 않았다. 그리드를 쓰지 않겠다는 후속 댓글은 사용자 논의 맥락이며 약관의 법적 판단을 별도로 수행한 것은 아니다.

## 브라우저·현재 공개 API 확인

- 사용자가 연 `d9c65c92b701450ff4e6c86b0ca7c932` 방송 탭을 직접 확인했다. 사용자 탭은 탐색 종료 후 유지하며 설정·로그인·그리드 권한을 변경하지 않았다.
- 페이지 DOM과 현재 리소스 목록에서 `nvelop-livecloud.pstatic.net`의 m3u8, `_HLS_msn`/`_HLS_part` 재생목록 요청, `.m4v` 부분 조각을 확인했다. 이 관찰은 CDN을 통한 LL-HLS 재생 경로의 근거이며 모든 브라우저/채널의 전송 방식을 일반화하지 않는다.
- 페이지가 실제 불러온 NAVER 공개 번들 `index-VdvK-ysl.js`와 `player-vendor-B7YwD4RF.js`를 `/tmp/chzzk-issue82-analysis/`로 받아 정적으로 읽었다. 실행하지 않았다. 플레이어는 HLS/LLHLS 및 P2P 트랙을 구분하고, 타임머신 재생 정보는 별도로 요청한다. `__bgda__` 처리 코드도 있다.
- 인증 정보를 넣지 않은 `/service/v3/channels/{channel_id}/live-detail` 응답은 HTTP/API 200, `OPEN`, `meta.cdnInfo.cdnType=NVELOP`, `HLS`/`LLHLS` media를 제공했다.
- 당시 1080p 일반 HLS variant는 약 4.167초짜리 조각 8개, 총 33.335초, target duration 10초, `EXT-X-MAP`이 있는 fMP4였다. 이 스냅샷에는 `EXT-X-DISCONTINUITY`가 없었다.
- media metadata에서 720p/1080p는 `p2pPath`가 있고 480p/360p/144p에는 없었다. 일반 HLS 1080p 조각 4개도 모두 HTTP 200으로 읽혔다. P2P metadata만으로 CDN의 고화질 실패를 단정하지 않는다.
- `timeMachineActive=True`와 실제 과거 조각 접근 가능성은 다르다. 인증 없는 `/service/v1/channels/{channel_id}/live-playback-json`은 API 200이지만 playback `live.timeMachine=False`이며 같은 약 33초짜리 일반 HLS를 반환했다. 이번 조회로 장시간 복구용 타임머신 사용 가능성을 확인하지 못했다.
- 쿠키·계정 토큰을 읽거나 사용하지 않았고, 서명된 스트림 URL 및 개인 설정은 저장소 기록에 보존하지 않는다.

## 코드 대조

- `plugin/chzzk.py:Chzzk._get_live()`는 `mediaId=HLS`, `protocol=HLS`만 선택한다. `ChzzkHLSStreamWorker._fetch_playlist()`는 재생목록 오류 시 API로 URL을 갱신하지만 개별 영상 조각의 실패 처리는 기본 writer에 맡긴다.
- `chzzk_record.py:record_stream()`은 조각 재시도 6회, timeout 15초, 출력 timeout 90초, `--hls-live-restart`를 사용한다. Streamlink 종료 뒤 FFmpeg 정리, 새 파일, 새 Streamlink 프로세스로 재시작하며 마지막 성공 조각 위치를 다음 프로세스에 전달하지 않는다.
- 약 33초의 sliding playlist에서 장시간 정체 뒤 재시작하면 이미 목록을 벗어난 조각을 단순 live restart로 되찾을 수 없다. `--hls-live-restart`는 현재 제공된 목록의 가장 앞을 선택하며 녹화기의 마지막 성공 위치에서 이어받는 기능이 아니다.
- Streamlink 8.6.2 공식 `HLSStreamWriter.fetch()`는 재시도 실패를 로그로 남기고 `None`을 반환한다. `SegmentedStreamWriter.run()`은 결과가 없으면 그 조각을 쓰지 않고 다음 큐 항목으로 넘어간다. `SegmentedStreamWorker.check_sequence_gap()`은 경고를 남기지만 누락 조각을 복구하지 않는다.
- 공식 치지직 플러그인은 `timeMachineActive`에 따른 별도 playback 조회 및 해당 경로의 `.m4v` 요청에 `__bgda__` 전달을 구현한다. 현재 프로젝트의 override에는 이 경로가 없다. 현재 일반 HLS 조각은 이 처리 없이도 HTTP 200이므로 `__bgda__` 누락을 이번 장애의 확정 원인으로 단정하지 않는다.
- FFmpeg의 `+genpts+discardcorrupt`, stream copy, TS timestamp 옵션은 수신하지 못한 프레임을 생성하지 않는다. 반환 코드 0은 전달된 입력의 처리 완료를 의미하며 방송 전체의 연속성 보장은 아니다.
- 이슈 로그의 입력 `Duration`과 큰 `start` 값은 라이브 fMP4 입력 메타데이터다. 이를 해당 녹화 파일의 실제 보유 프레임 길이로 해석하지 않는다.

## 실제 조각을 이용한 누락 재현

- 공개 방송 1080p의 init map 1개와 연속 영상 조각 4개를 읽었다. 모두 HTTP 200이며 영상 조각은 각각 약 4.27MB, 이번 요청 시간은 0.148~0.445초였다. 이 짧은 측정은 신고자 네트워크나 장시간 안정성을 검증하지 않는다.
- 진단 스크립트와 자료는 `/tmp/chzzk-issue82-analysis/probe_segments.py`, `intact.mp4/.ts`, `missing-one.mp4/.ts`에 있다. Streamlink 실행 없이 init+fragment 바이트를 stdin으로 보내 현재 코드의 원본 유지·TS 출력 옵션과 같은 핵심 FFmpeg 옵션을 사용했다. 환경은 Linux FFmpeg n9.0.2다.
- 정상 조각 4개: FFmpeg 반환 코드 0, TS 길이 16.707334초, 영상 패킷 1,000개, 패킷 duration 합계 16.667초, PTS 공백 없음.
- 두 번째 조각을 의도적으로 제외한 경우: FFmpeg 반환 코드 0, stderr 경고 없음, TS 길이 16.707334초 유지, 영상 패킷 750개, 패킷 duration 합계 12.5003초, PTS 간격 4.183초.
- 별도 `ffprobe -count_frames` 디코딩 검사에서도 정상 입력 1,000프레임, 조각 누락 입력 750프레임을 확인했다.
- 이 실험은 파일 표시 길이가 그대로여도 실제 영상이 빠진 상태로 성공 처리될 수 있음을 재현했다. 원래 신고 파일의 실제 누락 지점이나 YouTube 처리 결과까지 재현한 것은 아니다.

## 결정·남은 작업

- 수신 연속성 문제와 디스크 부족 처리를 분리해서 개선한다. 제안은 `.ai/plans/issue82-hls-continuity.md`에 두며 구현 완료 또는 사용자 합의 사항으로 취급하지 않는다.
- 런타임 변경 전 원본 TS의 패킷 PTS, 누락 조각 로그, 파일 전환 원인을 대조하는 것이 다음 확인 지점이다. 제공된 일부 로그만으로 4시간 43분 → 2시간 48분 차이의 원인 전체는 확정하지 않는다.
- 실제 녹화기 프로세스를 통한 장시간 CHZZK 녹화, 신고자의 macOS FFmpeg 9.0.1 환경, Windows, YouTube 업로드, 글로벌 CDN 전환, 장애 후 과거 조각 복구는 미검증이다. 현재 checkout에는 `.venv`가 없고 시스템 Python에 Streamlink가 설치되지 않아 실제 설치 API 검증은 하지 않았다. 버전 8.6.2의 공식 소스와 lockfile을 대조했다.
- 저장소 변경은 작업 기록·수정 제안·Knowledge의 연속성 주의점이다. `git diff --check`와 새 문서까지 포함한 줄 끝 공백 검사 모두 통과했다.

## 주요 외부 근거

- [Streamlink 8.6.2 CLI](https://streamlink.github.io/cli.html#cmdoption-hls-live-restart)
- [Streamlink 8.6.2 치지직 플러그인](https://github.com/streamlink/streamlink/blob/8.6.2/src/streamlink/plugins/chzzk.py)
- [Streamlink 8.6.2 HLS writer](https://github.com/streamlink/streamlink/blob/8.6.2/src/streamlink/stream/hls/hls.py)
- [Streamlink 8.6.2 segmented writer/worker](https://github.com/streamlink/streamlink/blob/8.6.2/src/streamlink/stream/segmented/segmented.py)
- [NAVER 페이지 번들](https://ssl.pstatic.net/static/nng/glive/resource/p/static/js/index-VdvK-ysl.js)
- [NAVER 플레이어 번들](https://ssl.pstatic.net/static/nng/glive/resource/p/static/js/player-vendor-B7YwD4RF.js)

## 구현 승인 후 결과

- 사용자 요청이 사전 분석에서 다중 CDN/누락 복구/선택적 과거 1시간 시작의 실제 구현으로 확대되었다. 2초 hedge, 30초 API 갱신, 90초 무진행 복구 실패, 전역 false/채널 null·true·false, 세션 내 방송별 한 번의 과거 시작과 안전한 파일 전환을 승인했다.
- 사용자가 타임머신이 없는 예시로 강지 채널과 이후 응가황제 채널을 제공했다. `timeMachineActive`만으로 제한하지 않고 API에 광고된 긴 목록과 실제 조각 접근을 추가 확인했다. 아래는 2026-10-10 조회 당시 값이며 영구 서비스 정책이 아니다.

| 채널 | 공개 채널 ID | 타임머신 플래그 | 일반 목록 | 긴 목록 | 가장 오래된 전체 조각 검증 |
| --- | --- | --- | --- | --- | --- |
| 강지 | b5ed5db484d04faf4d150aedd362f34b | false | 8개, 약 33.335초 | 864개, 약 3,598초 | 3,231,056바이트, 영상 250·음성 196프레임, ffprobe 0 |
| 응가황제 | d7390b4ecd61e8f04bd80d5e414637f6 | false | 15개, 30초 | 300개, 600초 | 2,664,056바이트, 영상 120·음성 94프레임, ffprobe 0 |
| 이터널 리턴 공식 | d9c65c92b701450ff4e6c86b0ca7c932 | true | 8개, 약 33초 | 약 3,599초 | 4,272,235바이트, 영상 250·음성 195프레임, ffprobe 0 |

- 길이가 긴 목록은 `live-detail.livePlaybackJson`의 HLS `encodingTrack.p2pPath`에 인코딩된 `cdn_url`이었다. 실제 API가 광고한 HTTP CDN URL을 추출한 것이며 P2P/그리드 프로그램을 실행하지 않았다. 초기 `live-playback-json`만 조회했을 때 약 33초밖에 확인하지 못한 것과 조회 경로가 다르다.
- init+가장 오래된 전체 fragment를 내려받아 실제 영상·음성을 디코딩했다. 목록 길이만으로 접근 가능하다고 주장하지 않는다. 긴 목록 전체 1시간을 모두 내려받은 검사는 아니다.

## 실제 변경

- `hls_continuity.py`: API 광고 후보 pool, 화질/방송/시각/길이/init 대응, 완전 수신 검증, 최대 두 요청의 hedge, 순서대로 한 번 출력, 현재·긴 목록의 누락 복구를 구현했다. 현재 cursor는 큐 위치가 아닌 writer의 성공 출력 위치다.
- 기본 writer의 실패 `None` 생략 경로를 대체했다. init과 media를 HTTP 길이/TS 패킷/BMFF box 경계로 검증하며 fMP4에 init이 빠지면 거부한다. 대체 init은 SHA-256으로 비교한다. 런타임에서 모든 조각을 별도 디코딩하는 것은 아니다.
- 예비 목록/API 조회가 늦거나 일시 실패해도 진행 중인 주 요청을 기다려 사용할 수 있도록 조회를 분리했다. 토큰 갱신은 동시 실패 사이에 공유하며 예비가 먼저 성공해도 갱신을 시도한다. 느리게 보내는 본문에도 전체 요청 시간 제한과 중지 검사가 동작하도록 urllib3 `read1()`을 사용한다.
- 출력 스레드 수, 20개 큐, 미디어 요청 semaphore, 제한된 manifest 조회를 사용한다. CLI의 Streamlink 다운로드 스레드는 해당 버전 상한 10으로 제한한다. 후보 pool은 역할별 origin 두 개/origin별 경로 두 개다.
- `plugin/chzzk.py`: 기존 권한/쿠키 검사를 유지하고 광고된 CDN 주소·플래그를 연결했다. 주기적 갱신으로 대체된 기존 미사용 만료시간/worker 코드와 import를 정리했다.
- `recording_continuity.py`: URL 없는 버전 1 stderr 이벤트 검증, 방송별 최초 과거 시작과 resume를 관리한다. `chzzk_record.py`는 `--hls-live-restart`를 제거하고 새 인자를 연결한다. 파이프와 stderr를 비운 후 FFmpeg·파일 정리를 끝내며 boundary면 다음 위치/latest에서 새 파일을 생성한다.
- `recording_options.py`/`config_store.py`: 전역 false 및 채널 nullable strict boolean 상속. `previous_hour_for_start()`는 장시간 대기 중 변경된 설정도 다음 방송 시작에 반영한다.
- `settings.py`/`gui/settings_dialog.py`/`i18n.py`: 전체와 채널 설정, 도움말/F1/접근성, 새 시작·복구·공백·전환 로그를 5개 언어에 추가했다. Qt는 공용 녹화 코어로 가져오지 않았다.
- 5개 README와 합의된 구현 계획·Knowledge를 갱신했다. 기존 소개·Android 튜토리얼 내용은 유지한다. 실제 인증 정보·서명 URL·개인 설정은 기록하지 않는다.

## 수행한 검증

- 잠금파일을 유지해 `uv sync --locked --offline --extra gui`로 검증 환경을 만들었다. Python 3.12.15, Streamlink 8.6.2, Qt/PySide6 6.11.2, Linux FFmpeg n9.0.2. 의존성 파일은 변경하지 않았다.
- `CHZZK_TEST_MEDIA=/tmp/chzzk-issue82-analysis/intact.mp4 .venv/bin/python -m unittest discover -s tests -q`: **37개 통과, 실패/건너뜀 0**. 이전 실방송 fMP4 입력을 사용했다. 입력이 없을 때는 테스트가 FFmpeg로 동일한 1,000프레임 합성 fixture를 생성한다.
- HTTP fault 검사: 주 CDN 지연/503, 예비 성공, body 중단·trickle, 목록 jump와 긴 목록 복구, 일부 복구 후 남은 공백, 복구 불가, init 차이, discontinuity, 방송·화질 차이, 시각 부재, 토큰/URL 갱신 및 API 일시 실패, 조회 지연·실패, 방송 종료, 사용자 중지. 출력 바이트·순서·중복과 요청 상한을 확인했다.
- 이전 fMP4의 사라진 두 번째 조각을 복구한 출력은 원본과 바이트가 같다. 실제 FFmpeg TS 출력과 ffprobe 디코딩은 **영상 1,000프레임**, 음성 700프레임 이상, 영상 PTS 최대 간격 0.04초 미만/음성 0.06초 미만이었다. 누락 재현의 750프레임과 구분했다.
- 실제 녹화 관리자 통합 검사: child Streamlink reader → recorder pipe → 실제 FFmpeg → 파일 정리를 실행했다. discontinuity 전환은 정상 TS 두 개 각 500프레임, 복구 불가능한 누락은 경고와 최신 위치의 TS 두 개 각 250프레임이다. `.part`가 남지 않았고 두 번째 과거 옵션은 0이었다. 전자는 resume 시각을 전달하고 후자는 전달하지 않았다.
- 설정 검사: 전역/채널 상속·JSON boolean, 부족한/부재/404 과거 분량, false 타임머신 플래그에서 실제 과거 사용, 재연결 중복 방지, 새 방송 적용, 대기 중 설정 갱신, 이벤트 입력 검증, 5개 언어 문자열을 확인했다.
- Qt offscreen: 5개 언어에서 실제 SettingsDialog 전체 on/off 및 ChannelDialog 상속/on/off 로드·저장 모두 통과했다. 사용자 설정 파일에 저장하지 않았다.
- 프로젝트 Streamlink CLI 플러그인 로드와 실제 8.6.2 reader/writer 호환을 확인했다. 변경된 Python 파일의 `py_compile`, `git diff --check` 및 새 파일까지 포함한 whitespace 검사도 수행했다.

### 짧은 실방송 녹화

공개 계정 없이 실제 `.venv/bin/python -m streamlink --plugin-dirs plugin --stdout`를 FFmpeg에 연결했다. 실행 중 서비스를 변경하거나 장애를 강제로 넣지 않았다.

| 실행 | 시작 옵션 | Streamlink / FFmpeg | 재생시간 | 디코딩 영상 / 음성 프레임 |
| --- | --- | --- | --- | --- |
| 응가황제 현재 위치 | 0 | 0 / 0 | 16.001초 | 960 / 750 |
| 강지 약 1시간 전 | 3600, 제공 3,598.083초 | 0 / 0 | 16.700334초 | 1,000 / 781 |
| HTTP 읽기 보강 후 응가황제 현재 위치 | 0 | 0 / 0 | 8.006334초 | 480 / 375 |
| HTTP 읽기 보강 후 강지 약 1시간 전 | 3600, 제공 3,598.150초 | 0 / 0 | 8.372667초 | 500 / 390 |

- 각 실행의 FFmpeg 오류 로그는 0줄이었다. 두 false 플래그 채널에서도 현재/과거 시작 이벤트가 올바른 시각을 전달했다. 1시간 전체 다운로드나 장시간 장애 안정성을 검증한 결과는 아니다.
- 진단 자료와 녹화는 `/tmp/chzzk-issue82-analysis/`, `/tmp/chzzk-issue82-validation/`에만 있다. 저장소에는 대용량 영상/서명 URL을 추가하지 않았다.

## 현재 한계와 작업 범위

- 장시간 녹화, Windows/macOS, 실제 회원 전용 계정, YouTube 처리, 원 신고 파일 전체, 실제 방송에서 CDN 장애를 강제한 검증은 수행하지 않았다. 신고의 4시간 43분 → 2시간 48분 차이를 모두 설명하거나 기존 누락 파일을 소급 복원했다고 주장하지 않는다.
- 서비스의 복수 CDN/과거 보관은 가변적이다. `timeMachineActive=false`에서도 실제 접근할 수 있었지만 다른 채널·날짜·화질·권한에 보장되지 않는다.
- 런타임은 구조/완전성 검증이며 모든 조각의 codec decode 검증은 아니다. implicit-offset byte range와 AES-128 외 암호화는 명시적 실패로 처리한다. AES-128 암호화된 실방송은 검증하지 않았다.
- 프로세스 강제 종료 후 커서를 영구 복원하는 기능은 포함하지 않았다. 기존 파일 정리/디스크 부족 정책은 유지한다. 원격 게시·커밋·push·PR·이슈 댓글은 실행하지 않았다.

## dev 게시 준비 (사용자 후속 승인)

- 2026-10-10 사용자가 이번 구현을 커밋하고 `dev` 브랜치에 push하도록 명시적으로 승인했다.
- 최신 원격 조회/fetch에서 `origin/dev=f9a2f528bb2b18776bec5a9e6bc5d36b9a761ff5`, `origin/main=9fb880ebf3baef9a3dbcbe83b05c2db1a0b57e19`를 확인했다. 기존 dev는 현재 main의 조상이며 main에 36개 후속 커밋이 있다.
- 현재 검증한 main 기준으로 로컬 `dev`를 만들고 기존 dev 이력을 보존하는 일반 push를 준비했다. main의 로컬/원격 ref는 변경하지 않는다.
- 게시 전 `.venv/bin/python -m unittest discover -s tests -q`를 외부 재현 입력 없이 실행했다. 합성 fMP4 생성 및 실제 FFmpeg 경로를 포함한 37개 검사 통과, 실패/건너뜀 0이다. Python 컴파일과 `git diff --check`도 통과했다.
- 이번 기능·검증·5개 언어 사용법·`.ai` 문서 18개 파일만 커밋 대상으로 확인했다. 원격 게시 결과와 SHA 검증은 실제 push 후 이어 기록한다.

## dev 게시 결과

- Git CLI push는 HTTPS 인증 정보가 없어 실패했다. 동일한 실패를 반복하지 않고 사용자 승인 범위 안에서 연결된 GitHub 도구로 게시했다.
- 로컬 구현 커밋 `4d8abae196db2b5c834d8309f8080ac91d03b298`은 `codex/issue82-local-before-publish` 로컬 브랜치에 보존했다. API의 커밋 메타데이터가 달라 원격 구현 커밋 SHA는 `868dc5864a772865de1b546b6b495799c64b5aba`다.
- 양쪽의 전체 tree SHA는 `33267728be5e0dfd01fca61aac7f3ac4f6e12e92`로 정확히 같다. 18개 파일 내용과 부모 main 커밋을 검증한 후 원격 dev를 갱신했다.
- `expected_sha=f9a2f528bb2b18776bec5a9e6bc5d36b9a761ff5`, `force=false`로 기존 dev 이력을 보존했다. `git ls-remote origin refs/heads/dev`는 원격 구현 SHA와 일치했다.
- fetch 후 로컬 dev를 같은 내용의 API 커밋으로 맞추고 upstream을 `origin/dev`로 설정했다. 로컬 HEAD·origin/dev·원격 dev가 모두 `868dc5864a772865de1b546b6b495799c64b5aba`임을 확인했고 작업 트리는 깨끗했다.
- 로컬/원격 main은 모두 `9fb880ebf3baef9a3dbcbe83b05c2db1a0b57e19`로 유지했다. PR·main 병합·이슈 댓글은 실행하지 않았다.
- 게시 전 기본 경로의 37개 테스트, Python 컴파일, staged diff whitespace 검사가 통과했다. 기존 장시간/Windows/macOS 미검증 범위는 유지한다.
- 이 게시 결과 기록은 dev의 별도 문서 커밋으로 보관한다. 문서 커밋 뒤 원격 SHA와 로컬 HEAD를 다시 확인한다.
