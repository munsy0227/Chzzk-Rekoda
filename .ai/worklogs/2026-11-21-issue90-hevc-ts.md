# 이슈 #90 HEVC TS 원본 저장

- 확인일: 2026-11-21 (Asia/Seoul). 사용자 지정 채널의 HEVC TS 원본 저장 오류를 분석·수정했다. Rust 기능은 먼저 일반 병합 커밋 `aa5794d`로 원격 main에 반영했고, 해당 [병합 Actions](https://github.com/munsy0227/Chzzk-Rekoda/actions/runs/44773738744)의 6개 회귀 작업이 모두 통과했다.
- [이슈 #90](https://github.com/munsy0227/Chzzk-Rekoda/issues/90)의 TS 실패는 `chzzk_record.py:record_stream()`이 원본 복사에도 `h264_mp4toannexb`를 강제한 데서 발생했다. 이를 제거하면 [FFmpeg MPEG-TS muxer](https://ffmpeg.org/ffmpeg-bitstream-filters.html#hevc_005fmp4toannexb)가 실제 입력 코덱에 맞는 Annex B 필터를 삽입한다. 단일·분할 TS에 같은 복사 경로를 사용한다.
- 두 공개 live-detail 응답에 1080p60 HEVC·H.264가 함께 있었다. 첫 채널에서 Streamlink의 `best` 캡처는 HEVC/AAC, `1080p60_alt` 캡처는 H.264/AAC였다. 실제 H.264 샘플도 필터 강제 없이 TS 복사하고 전 구간 디코딩했다.
- 합성 fMP4에서 이전 명령은 HEVC 단일·분할 모두 H.264 필터 불일치로 실패했다. 수정한 명령은 H.264와 HEVC 각각 단일·분할 네 경우에 영상 90프레임과 AAC를 정상 저장·디코딩했다.
- `tests/test_recording_stop.py:RealStopTests.test_copy_hevc_fragment_to_ts()`로 로컬 HLS → 실제 녹화기 → FFmpeg → 정상 종료를 검증한다. 동일 테스트는 수정 전 TS가 생성되지 않아 실패했고 수정 후 코덱·프레임·PTS·전체 디코딩이 통과했다. 기존 MKV 종료 검사 5개는 FFmpeg 9.1이 null 디코딩 출력에 MKV의 DURATION 메타데이터를 복사할 때 나오는 경고로 실패했으므로 시험 출력의 메타데이터 매핑만 해제했다. 13개 종료 집중 검사 통과.
- 최종 변경에서 Python 201개 중 199개 통과, 호스트 전용 2개 제외, 실패 0이었다(`.cache/issue90-full-tests.log`). 수정한 Python 파일 문법 및 `git diff --check`도 통과했다.
- 빈 쿠키 설정의 격리된 Linux 실행에서 Rust 상태 조회와 한국 CDN 부분 조각 경로를 사용했다. `e4b12ad6a22d3e8d1dd8a79522cca667` 단일 TS 130.069초, `628cc9ec2a5a59cd238c0df9315e8ee0` 1분 분할 TS 62.059/60.043/8.032초를 저장했다. 모두 1920×1080 60fps HEVC와 AAC로 확인했고, 4개 파일 전체 디코딩과 정상 종료(강제 종료 없음)를 통과했다. 연속성 체크포인트 130개, 공백·미해결·중복·오류 모두 0이었다. 녹화 중 5초 위치에서 분할 TS는 자동으로, 단일 TS는 임시 `.part` 파일을 직접 열어 프레임을 읽었다. 최초 시험 스크립트는 `.part`를 탐색 목록에서 누락해 마지막 자동 확인만 실패했다. 로그 `.cache/issue90-live-result.log`.
- MKV의 녹화 중 인덱스 생성과 플레이어별 탐색 동작은 별개다. 이번 확인은 FFmpeg 탐색과 실제 파일 디코딩으로 제한한다. Windows·macOS에서의 실방송 녹화와 장시간 동작은 확인하지 않았다.
