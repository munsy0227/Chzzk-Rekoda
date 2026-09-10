# GUI 설정 대응표

확인: 2026-09-10. 기존 `settings.py`에서 `config_store.py`로 옮긴 `default_config`, `normalize_config()`, `ENCODER_PRESETS` 및 CLI 메뉴를 기준으로 한다.
사용자 요청: 리본 UI의 느낌을 유지하면서 기존 설정을 모두 제공한다.
확정 작업 범위: 최초 시안 완성 이후 사용자가 실제 Qt 구현과 채널 아이콘/녹화 미리보기를 요청했다. 현재는 전체 설정을 실제 파일에 연결했으며 [구현 기록](../worklogs/2026-09-08-qt-gui-implementation.md)에 검증 범위를 구분해 기록한다.

| 화면 | 기존 설정/기능 | 입력 규칙 |
| --- | --- | --- |
| 처음 설정 | `language`, 채널/저장 위치, `gui_settings.onboarding_completed` | 첫 실행에 표시, 완료 시에만 저장, 취소하면 기존 설정 유지; 채널 나중에 추가 선택 가능 |
| 채널 | 이름 검색, ID 조회, 추가, 목록, 삭제, 활성화 | ID 중복 방지, 저장된 파일 삭제와 등록 해제 구분 |
| 채널 상세 | `channels[].id/name/output_dir/active`, `delays` | 지연 0~3600초, 내부 `identifier`는 자동 관리 |
| 기본 녹화 | `output_format` | TS/MKV/WebM |
| 기본 녹화 | `recording_split_minutes` | 분할 안 함, 분/시간 단위, 0~10080분(최대 168시간) |
| 채널별 분할 | `channels[].recording_split_minutes` | 없음/null=전체 설정, 0=분할 끄기, 1~10080분 |
| 화질 | `quality_settings`, `channels[].quality_settings` | best/144p/360p/480p/720p60/1080p60/custom, 가로/세로 짝수, FPS 0 또는 1~120, 채널별 상속 |
| H.264 | `h264_settings.enable/encoder/bitrate/max_bitrate/preset` | 인코더 6종, HEVC/AV1과 상호 배타, WebM 지정 시 MKV |
| 백그라운드 | `gui_settings.close_to_tray` | 닫기 시 트레이 유지, 없으면 종료; '녹화 중지'/'종료' 모두 기존 파일 정리 대기 |
| 앱 종료 | 설정 리본의 프로그램 완전 종료 | 녹화 및 로그인 자식 정리 후 트레이까지 종료 |
| 녹화 용량 | 현재 작업의 `total_bytes`/`total_size` | 분할 녹화는 현재 작업에서 생성한 모든 분할 파일의 실제 크기 합산 |
| 기본 녹화 | `timeout` | 1~3600초, 기본 60초 |
| 기본 녹화 | `stream_segment_threads` | 1~16, 기본 2 |
| HEVC | `enable/encoder/bitrate/max_bitrate/preset` | 인코더 6개, 인코더별 프리셋, H.264/AV1 활성화와 상호 배타 |
| AV1 | `enable/encoder/bitrate/max_bitrate/preset` | 인코더 6개, 인코더별 프리셋, H.264/HEVC 활성화와 상호 배타 |
| 네이버 로그인 | Chrome/Edge/Firefox 로그인, `cookies.NID_AUT/NID_SES` | CLI 로그인 창에서 로그인 후 Enter → GUI 편집 화면에 전달 → 저장; 수동 입력/마스킹/값 삭제도 유지 |
| 네트워크 | `dns_settings.enable/doh_url` | HTTPS 주소, 기본 주소 복원 |
| 언어/로그 | `language`, `log_enabled` | 한국어/영어/간체/정체/일본어, 파일 로그 저장 여부 |

## 설치 및 CLI 대응

- 설치 마지막에 GUI/CLI를 선택한다. GUI 선택은 Qt 설치 후 첫 실행 마법사, CLI 선택은 기존 설정 메뉴로 연결한다. Windows GUI 진입점은 콘솔을 숨기는 `chzzk_gui.vbs`이며 `.bat`도 같은 진입점으로 연결한다.
- Linux는 설치 폴더의 `Chzzk-Rekoda.desktop`을 클릭해 실행한다. TTC의 CJK family를 언어별로 선택하며 Windows는 DirectWrite와 모니터별 DPI를 지정한다. 검증 범위는 [플랫폼 개선 기록](../worklogs/2026-09-10-gui-platform-fixes.md)을 참고한다.
- CLI 최상위 메뉴는 1 채널, 2 녹화·화질, 3 인코딩, 4 NAVER 로그인, 5 네트워크, 6 언어·로그다. 0번은 모든 하위 메뉴에서 뒤로, 최상위에서는 종료다.
- 인코딩 메뉴는 H.264/HEVC/AV1에 같은 입력 순서와 검증을 적용한다. 채널 메뉴 4번에서 채널별 분할·화질을 설정한다.
- 제목 TXT는 파일명 길이 제한으로 제목이 축약된 녹화에만 생성한다. 사용법과 검증 범위는 [설치·마법사 기록](../worklogs/2026-09-09-install-onboarding.md)을 참고한다.

## 인코더와 프리셋

- H.264: libx264, h264_nvenc, h264_qsv, h264_amf, h264_vaapi, h264_videotoolbox.
- HEVC: libx265, hevc_nvenc, hevc_qsv, hevc_amf, hevc_vaapi, hevc_videotoolbox.
- AV1: libsvtav1, libaom-av1, av1_nvenc, av1_qsv, av1_amf, av1_vaapi.
- 프리셋 목록 및 기본값은 현재 `ENCODER_PRESETS`, `ENCODER_DEFAULT_PRESETS`와 대조한다.
- VAAPI/VideoToolbox처럼 프리셋 선택을 지원하지 않는 항목은 `auto`와 비활성 이유를 표시한다.
- 인코더 변경 시 유효한 기존 프리셋은 유지하고, 지원하지 않으면 해당 인코더의 기본값으로 바꾼다.
- 하드웨어 인코더가 목록에 있다는 사실은 실행 가능 여부의 보증이 아니다. 시안에서 실제 probe 성공을 표시하지 않는다.

## 시안 완료 기준

- 모든 설정에 조작 가능한 입력과 설명을 제공한다.
- 화면 내 임시 설정을 저장/취소하고 다시 열어 값을 확인할 수 있다.
- 입력 범위/URL/비트레이트 검증, 인코더별 프리셋, HEVC/AV1 상호 배타를 확인한다.
- 채널 검색/브라우저 로그인/폴더 선택처럼 외부 연결이 필요한 작업은 예시 또는 연결 전 상태를 명시한다.
- 실제 설정 파일 저장, 실제 로그인, 녹화 실행, 제품의 5개 언어 번역 구현과 시안 완성을 혼동하지 않는다.
