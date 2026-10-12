# 녹화 CI 채널 입력과 최신 안정 OS

확정: 2026-10-11. 사용자가 아래 계획 전체의 구현을 승인했다. 실행 결과는 [작업 기록](../worklogs/2026-10-11-recording-test-platforms.md)에 남긴다.

- 두 수동 workflow에 선택 `channel_uuid`와 `test_os=linux/windows/macos/all`을 추가한다. UUID는 공백 제거 후 비어 있으면 기존 `64a90ba95d1f9feb0a798a20bbf0f40c`, 입력됐으면 32자리 16진수 검증을 적용한다. OS 기본값은 Linux다.
- 사용자가 고른 버전 기준은 GitHub의 `ubuntu-latest`, `windows-latest`, `macos-latest`다. `all`은 병렬 실행하고 `fail-fast: false`로 OS별 결과를 얻는다. latest는 OS 공급자의 최신 출시판과 다를 수 있는 GitHub 안정 이미지 기준이다.
- 장시간 270~330분(기본 300), 코덱별 5~20분(기본 10), 기존 job timeout·공용 concurrency·uv 잠금 설정을 유지한다.
- FFmpeg는 apt/Homebrew, Windows는 SHA-256 검증한 Gyan full 빌드를 사용한다. full은 libsvtav1을 포함한다. 기존 사용자용 Windows essentials 설치기를 바꾸지 않는다.
- Python 공통 실행기로 설정·정리·감시·판정을 이관하고 Bash의 세 인수 인터페이스는 래퍼로 유지한다. 기존 GUI 제어 프로토콜로 정상 중지하고 120초 초과 시 하위 프로세스도 정리하며 실패한다.
- 5분 분할, 180초 무출력 제한, 15초 감시, 60초 정리와 수정 후 15분이 지난 영상 삭제를 유지한다. JSONL/요약은 삭제하지 않는다. H.264 원본 복사·libx265/ultrafast·libsvtav1/13 및 실제 codec/연속성 판정을 유지한다.
- OS별 로그·보고서·요약·환경 버전을 실패에도 업로드하며 OS/run ID/run attempt로 이름을 구분하고 7일간 보관한다. 개인 설정과 인증 정보는 수정하거나 아티팩트에 담지 않는다.
- 정상·조기·무출력·강제 종료, 경로와 보존 범위, 입력·matrix·인코더·코덱 확인을 검증한다. 안내와 README 다섯 언어, 프로젝트 기록을 갱신한다.
- 실제 세 OS 실방송, 커밋·push·Actions 실행은 별도 요청 범위다.
