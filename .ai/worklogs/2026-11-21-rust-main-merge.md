# 선택형 Rust 기능 main 병합

- 확인일: 2026-11-21 (Asia/Seoul).
- 사용자 요청에 따라 `codex/rust-features`의 `149ade3`을 `main`의 `797820e`에 일반 병합한다. 원격 두 ref의 해시를 확인했고, 기존 main은 기능 브랜치의 조상이다. 내용 충돌 없이 병합했다.
- 병합 대상 Rust 기능 tip의 [Actions 43687517965](https://github.com/munsy0227/Chzzk-Rekoda/actions/runs/43687517965)는 정확한 SHA에서 3개 OS의 6개 작업이 모두 성공했다. 파일 분할·CDN·녹화의 별도 Rust 검증기는 제안 단계이며, 5시간 실방송과 새 OS의 관리자 설치는 이번 병합 검증 범위에 포함하지 않는다.
- 병합 상태에서 로컬 Cargo 검사 12개가 통과했다. Python 200개 중 193개 통과, OS 전용 2개 제외, 5개 실패였다. 모두 FFmpeg 9.1에서 기존 MKV 종료 검사의 빈 stderr 가정으로 실패했다. 병합 전 `797820e`를 별도 임시 폴더에 풀어 동일한 5개 실패를 재현했다. 로그는 `.cache/rust-main-merge-tests.log`와 `.cache/rust-main-baseline-stop.log`에 보관했다.
- 이슈 #90의 HEVC TS 원본 저장 수정은 별도 커밋으로 검증한다.
