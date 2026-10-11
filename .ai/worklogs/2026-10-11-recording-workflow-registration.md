# main 수동 녹화 워크플로 등록과 dev 실행

확인: 2026-10-11. 사용자는 dev push 후 `8557299`만 main에 체리픽해 수동 테스트를 진행하도록 요청했다.

## 확인 및 확정 범위

- 작업 트리는 깨끗했고 origin/main과 origin/dev를 fetch했다. main은 `9fb880e`, dev는 `8557299`이며 로컬 브랜치와 일치했다.
- main에는 `continuity_report.py`, `recording_continuity.py`, `tests/test_hls_continuity.py`가 없고 녹화기의 `--continuity-report` 옵션도 없다. 전체 커밋을 그대로 적용하면 새 실행기의 import부터 실패한다. merge-tree 사전 확인에서 워크플로·다섯 README·번역·Bash helper·연속성 테스트의 충돌을 확인했다.
- 사용자는 의존성 이식과 구분해 **"main에 등록만 하고 실제 테스트는 dev에서 실행"**을 선택했다. 따라서 `8557299` 중 두 워크플로 변경만 이식하고, 실행 코드와 의존성은 dev 체크아웃으로 가져온다.

## 실제 변경

- `git cherry-pick --no-commit 8557299`로 적용한 뒤 두 워크플로를 원본 커밋의 버전으로 해결했다. 그 외 적용 파일은 기존 main 버전으로 되돌려 dev 전용 실행기·테스트·문서가 main에 추가되지 않도록 했다.
- 두 워크플로의 checkout 단계에 `ref: dev`와 `Check out dev test code` 이름을 지정했다. main에서 수동 실행해도 dev의 Python 실행기·연속성 보고·FFmpeg 설치기를 사용한다. 실제 검사 버전은 checkout 단계에 기록되는 dev SHA이며, GitHub 실행 이벤트 자체의 ref/SHA와 구분한다.
- UUID·OS·시간 입력, matrix·fail-fast·잠금 의존성·작업 제한·공용 concurrency·실패 아티팩트 업로드와 7일 보존은 `8557299`의 내용이다. `.ai/KNOWLEDGE.md`에 main 등록과 dev 실행 관계를 기록했다.
- 적용 출처를 커밋 본문에 남기고 등록 범위를 설명하는 영어 메시지로 로컬 main에 한 커밋을 만든다. dev 브랜치의 커밋은 변경하지 않는다.

## 검증 및 남은 작업

- actionlint 1.7.12로 두 워크플로 문법을 통과했다(shellcheck 제외). YAML 구조를 `8557299`와 비교해 checkout 단계의 이름과 `ref: dev`만 다르고 나머지 설정은 동일함을 확인했다. UUID 기본값·네 OS 선택·Linux 기본값·fail-fast false·항상 업로드·7일 보존도 확인했다.
- origin/dev가 정확히 `8557299`이며 Python 실행기·Windows 설치기·연속성 모듈이 포함되어 있음을 확인했다. 충돌 인덱스가 비었고 `git diff --check`를 통과했다. 커밋 대상은 두 워크플로와 Knowledge·이번 작업 기록의 네 파일이다.
- 실행 코드는 이번 main 변경에 포함하지 않아 런타임 테스트를 다시 수행하지 않았다. dev의 앞선 검증 결과와 실제 OS/실방송 미검증 범위는 dev의 `2026-10-11-recording-test-platforms.md` 작업 기록을 따른다.
- push와 실제 Actions 실행은 수행하지 않는다. Windows/macOS·실방송 검증은 기존과 같이 원격 수동 실행 후 확인한다.
