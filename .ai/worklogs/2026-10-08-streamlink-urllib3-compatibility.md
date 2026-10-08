# PR #80 Streamlink/urllib3 호환 수정

- 확인일: 2026-10-08 (Asia/Seoul).
- 사용자 요청: urllib3 2.8.0 업데이트 PR #80에 Streamlink 8.6.2 업데이트를 함께 반영한다.
- 시작점: `dependabot/uv/urllib3-2.8.0`, 커밋 `0db3a3c7df9aeda81c008caba1d5f10256cb664f`.

## 원인과 변경

- 사용자 로그에서 Streamlink의 CHZZK API 요청이 `Urllib3UtilUrlPercentReOverride`의 `sub` 속성 누락으로 실패했다. FFmpeg의 빈 입력 오류는 스트림 수신 실패에 뒤따른 결과였다.
- `uv.lock`의 Streamlink 8.6.0 + urllib3 2.8.0 조합을 확인했다. Streamlink 공식 이슈 #7116, 수정 PR #7117 및 8.6.1 변경 기록과 일치한다.
- 사용자가 실제 실행 환경에 Streamlink 8.6.0이 남아 있음을 확인했고, 8.6.2로 업데이트한 뒤 정상 녹화를 확인했다.
- 같은 PR 커밋을 기반으로 별도 로컬 체크아웃을 만들고, 사용자가 uv로 갱신한 `uv.lock`을 반영했다. Streamlink를 8.6.2로 올리고 sdist 및 3종 wheel의 URL, SHA-256, 크기, 업로드 시각을 갱신한다. 다른 패키지 버전은 유지한다. 현재 uv가 생성한 lockfile revision 5를 유지한다.
- `.ai/KNOWLEDGE.md`에 호환 조합과 실제 녹화 환경에서 버전을 확인하는 기준을 기록한다.
- 확인한 관련 코드: `chzzk_gui`는 설치된 `.venv/bin/python`을 우선 사용하고, `process_utils.py:console_python()`은 현재 실행 중인 Python을 Streamlink 자식 프로세스에도 사용한다.

## 검증

- `uv --no-cache lock --offline --check`: 통과, 44개 패키지의 잠금파일과 프로젝트 메타데이터 일치 확인.
- 변경 전후 TOML 패키지 비교: Streamlink 외 패키지 내용과 최상위 설정 유지 확인. 최상위 revision만 uv 생성 결과인 3 → 5로 변경.
- `git diff --check`: 통과.
- 실제 설치 환경의 Streamlink 8.6.2 및 urllib3 2.8.0을 확인하고, Streamlink를 import한 상태에서 CHZZK API URL의 `parse_url()` 및 `HTTPSession.prepare_request()`를 실행했다. 네트워크 요청 없이 이전 오류가 발생한 URL 처리 경로를 검증했으며 통과했다.
- 실제 CHZZK 녹화 성공은 사용자 확인 결과다. 에이전트는 별도 실방송 녹화, Windows/macOS 녹화 및 장시간 녹화를 수행하지 않았다.

## 적용 범위

- 별도 로컬 체크아웃에 PR #80의 기존 커밋을 부모로 하는 추가 커밋을 준비한다. main 병합은 이 작업에 포함하지 않는다.
- GitHub `create_tree` 쓰기 요청이 `MCP tool call requires approval, but approval policy is never` 오류로 차단됐다. 원격 브랜치 및 PR 제목/설명은 변경되지 않았다.
- 남은 작업: 로컬 커밋을 `dependabot/uv/urllib3-2.8.0`으로 push하고, PR 제목/설명을 urllib3 및 Streamlink 동시 업데이트에 맞춰 정리한다. 도구의 승인 제한을 우회하는 원격 쓰기는 수행하지 않는다.
