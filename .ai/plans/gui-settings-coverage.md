# GUI 설정 대응표

확인: 2026-09-08. 기존 `settings.py`에서 `config_store.py`로 옮긴 `default_config`, `normalize_config()`, `ENCODER_PRESETS` 및 CLI 메뉴를 기준으로 한다.
사용자 요청: 리본 UI의 느낌을 유지하면서 기존 설정을 모두 제공한다.
확정 작업 범위: 최초 시안 완성 이후 사용자가 실제 Qt 구현과 채널 아이콘/녹화 미리보기를 요청했다. 현재는 전체 설정을 실제 파일에 연결했으며 [구현 기록](../worklogs/2026-09-08-qt-gui-implementation.md)에 검증 범위를 구분해 기록한다.

| 화면 | 기존 설정/기능 | 입력 규칙 |
| --- | --- | --- |
| 채널 | 이름 검색, ID 조회, 추가, 목록, 삭제, 활성화 | ID 중복 방지, 저장된 파일 삭제와 등록 해제 구분 |
| 채널 상세 | `channels[].id/name/output_dir/active`, `delays` | 지연 0~3600초, 내부 `identifier`는 자동 관리 |
| 기본 녹화 | `output_format` | TS/MKV/WebM |
| 기본 녹화 | `recording_split_minutes` | 분할 안 함, 분/시간 단위, 0~10080분(최대 168시간) |
| 기본 녹화 | `timeout` | 1~3600초, 기본 60초 |
| 기본 녹화 | `stream_segment_threads` | 1~16, 기본 2 |
| HEVC | `enable/encoder/bitrate/max_bitrate/preset` | 인코더 6개, 인코더별 프리셋, AV1 활성화와 상호 배타 |
| AV1 | `enable/encoder/bitrate/max_bitrate/preset` | 인코더 6개, 인코더별 프리셋, HEVC 활성화와 상호 배타 |
| 네이버 로그인 | Chrome/Edge/Firefox 로그인, `cookies.NID_AUT/NID_SES` | 수동 입력, 마스킹, 값 삭제; 실제 인증 성공 여부와 값 존재 여부를 구분 |
| 네트워크 | `dns_settings.enable/doh_url` | HTTPS 주소, 기본 주소 복원 |
| 언어/로그 | `language`, `log_enabled` | 한국어/영어/간체/정체/일본어, 파일 로그 저장 여부 |

## 인코더와 프리셋

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
