# 분할 용량, 다국어 폰트와 플랫폼 실행 개선

## 요청과 확인

- 사용자 요청(2026-09-09, 09-10 계속): 분할 녹화 GUI 용량 0 B, 제공 TTC 사용, Linux 폴더 클릭 실행, Windows High DPI 글자 흐림, 설정 리본 완전 종료 버튼, CMD 화면 점멸, Windows GUI의 FFmpeg 입력 오류 수정.
- 사용자가 CLI 연결 방식의 NAVER 로그인 정상 작동을 확인했다. 사용자 환경의 결과이며 에이전트가 실제 계정으로 로그인한 것은 아니다.
- 시작 브랜치 `gui`, HEAD `99b0757`. 이번 수정의 커밋·푸시는 요청되지 않았다. 원본 `02_NotoSansCJK-TTF-VF/`와 개인 녹화 폴더는 유지한다.
- 분할 muxer의 `total_size=N/A`를 `read_stream()`이 0으로 바꾸고 있었다. 실제 파일 합산으로 이 원인을 수정했다.
- 처음 제공된 Windows 로그의 `Invalid data found when processing input`과 Streamlink 코드 1만으로 최초 원인은 확정할 수 없었다. 이후 사용자가 전체 로그를 제공했으며 추가 Streamlink 로그는 없다고 확인했다. 새 로그 분석과 후속 수정은 아래에 기록한다.

## 변경 사항

- `chzzk_record.py:recording_output_size()`는 현재 분할 패턴의 실제 파일 크기를 합산한다. `read_stream()`은 분할 또는 알 수 없는 용량일 때 이를 사용하고 용량/속도/비트레이트 및 `total_bytes`를 갱신한다. 파일 정리 경합, 다른 녹화 제외, 제목의 리터럴 `%03d`를 처리한다. `recorder_bridge.py`가 GUI에 전달한다.
- 제공 TTC를 `font/02_NotoSansCJK-TTF-VF/Variable/OTC/NotoSansCJK-VF.ttf.ttc`에 복사하고 기존 KR 서브셋 TTF를 제거했다. 원본과 복사본의 바이트 일치를 확인했고 LICENSE를 유지했다. 원본 묶음의 다른 파일은 삭제하지 않았다.
- `gui/appearance.py`는 TTC의 JP/KR/SC/TC/HK 5개 family를 한 번 등록하고 언어별 우선순위를 선택한다. 마법사의 언어 변경에도 적용한다. Windows Qt 인자에 DirectWrite/모니터별 DPI를 지정하고 PassThrough 배율, 10pt 기본 폰트와 full hinting을 사용한다. 13px 기본 스타일을 제거해 point 크기를 유지한다.
- 설정 리본에 '프로그램 완전 종료'와 설명을 5개 언어로 추가했다. 기존 `quit_application()`으로 녹화와 로그인 정리를 기다린 후 트레이까지 종료한다.
- 실행 가능한 `Chzzk-Rekoda.desktop`은 `%k`로 자신의 위치를 받아 폴더 이동 후에도 실행기를 찾는다. 파일 URI/한글/공백/셸 문자를 직접 인자로 처리한다. `chzzk_gui`는 설치된 Qt 가상환경을 먼저 사용하고 uv의 사용자 설치 경로도 찾는다. 파일 관리자별 실행 허용 정책은 OS가 적용한다.
- CLI는 자동 갱신 스레드를 없애고 바뀐 내용만 초당 1회 별도 터미널 화면에 그린다. 종료 후 마지막 로그를 남긴다. `process_utils.terminal_display_mode()`는 Windows VT 처리를 활성화해 줄마다 지우는 legacy 렌더러를 피하고 종료 시 콘솔 모드를 복원한다.
- GUI의 `-u`는 JSON 프로세스에만 적용한다. Streamlink가 GUI에서만 `PYTHONUNBUFFERED=1`을 상속하던 차이를 제거하고 stdin을 DEVNULL로 분리한다. Streamlink/화질 조회에 콘솔 Python을 명시한다. 확인된 실행 환경 차이를 줄이는 수정이며 사용자 Windows 입력 오류의 원인이 확정된 것은 아니다.
- 5개 README에 TTC, Linux 클릭 실행, 완전 종료, 분할 합산 용량을 반영했다.

## 검증

- `.gui-validation/platform_fixes_check.py`: N/A 진행 정보의 1000 → 3000 → 6000 바이트 합산, 다른 파일 제외, 리터럴 `%03d`, JSON 전달, CLI 변경 없는 프레임 갱신 억제/alternate screen/종료 로그 통과.
- TTC 5개 family와 한글/간체/정체/일본어/라틴 글리프, 5개 UI 언어, 완전 종료 버튼, Windows Qt 인자, 이동 가능한 desktop 실행 통과. 한글·공백·`#`·`%`·따옴표·셸 문자 및 file URI 경로의 실제 실행을 확인했다.
- 150%와 200% offscreen Qt 검증 통과. 설정 리본 및 완전 종료 버튼 화면을 시각 점검했다. Linux 렌더링이며 Windows의 실제 개선 확인을 대신하지 않는다.
- 실제 FFmpeg의 짧은/긴 제목 × 단일/분할 녹화 4가지에서 기록 중 바이트가 양수이며 단조 증가함을 확인했다. 분할 각 4개, 단일 각 1개를 ffprobe로 확인하고 제목 TXT 조건도 통과했다. 결과 `.gui-validation/encoding-49c96j4j`, 로그 `split-size-media-check.log`.
- 실제 QProcess → JSON 중계 → Streamlink CLI(로컬 합성 파일 플러그인) → FFmpeg 분할 녹화 검증 통과. GUI가 `342.59 KB`/350808바이트를 수신하고 중지 후 모든 결과를 ffprobe로 확인했다. 결과 `.gui-validation/gui-pipeline-osxr5p_9`, 로그 `gui-pipeline-check.log`. 실제 CHZZK 통신은 이 검증에 사용하지 않았다.
- Windows API 모사로 VT 활성화, 예외 시 원래 모드 복원, 미지원 콘솔 fallback을 확인했다. GUI/Streamlink의 unbuffered 환경 제거와 콘솔 Python 선택도 검증했다(`windows_flags_check.py`).
- 기존 JSON 중지/부모 EOF, GUI 로그인 출력·오류·취소, 로그인 창이 있을 때 트레이 종료 대기 회귀 검증 통과(`platform-process-check.log`). Python compileall, Ruff E9/F 및 GUI·공용 파일 import/format, shell 문법, desktop-file-validate, git diff --check 통과. 제공 TTC/라이선스와 배포본의 일치도 확인했다.
- [150% 설정 화면](../assets/qt-gui-dpi-settings.png), [중국어 글꼴 화면](../assets/qt-gui-cjk-font.png)을 기록했다. 모두 합성 채널을 사용했다.

## 참고와 남은 확인

- [Qt High DPI](https://doc.qt.io/qt-6/highdpi.html), [QFont](https://doc.qt.io/qt-6/qfont.html), [DirectWrite/가변 폰트](https://www.qt.io/blog/text-improvements-in-qt-6.7), [Desktop Entry Exec](https://specifications.freedesktop.org/desktop-entry/latest/exec-variables.html)을 확인했다. 로컬 Rich `live_render.py`/`live.py`의 줄 지우기/화면 커서 이동 경로도 대조했다.
- 실제 Windows GUI 입력 실패, High DPI 글자와 CMD 점멸은 해당 플랫폼에서 재검증이 필요하다. Linux 파일 관리자별 최초 실행 허용 UI는 tty 환경에서 미검증이다.
- 개인 설정/쿠키/녹화 파일은 수정하지 않았고 이번 변경은 커밋·푸시하지 않았다.

## 전체 Windows 로그를 받은 후 통신 경로 수정

- 사용자 제공 로그 순서는 11:33:23.340 녹화 시작 → .561 종료 신호 → .607 FFmpeg 빈 입력 오류 → .629 녹화기 종료다. 종료가 오류보다 앞선다. Windows `main()`의 종료 호출 경로를 조사했고, 기존 `JsonBridge`는 명시적인 stop, stdin EOF/길이 초과, stdout 쓰기 실패를 모두 동일한 종료 신호로 기록하고 있었다. 로그만으로 그 분기까지 구분할 수는 없다.
- [Qt 6.11 QProcess Windows 소스](https://raw.githubusercontent.com/qt/qtbase/6.11/src/corelib/io/qprocess_win.cpp)의 `qt_create_pipe()`는 자식 측 핸들도 `FILE_FLAG_OVERLAPPED`로 연다. [Microsoft ReadFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile) 및 [WriteFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-writefile)은 이 핸들에서 유효한 OVERLAPPED 구조 없이 호출하면 완료 여부를 잘못 보고할 수 있다고 명시한다. 이는 코드에서 확인한 호환성 문제이며 사용자의 실제 종료를 이 분기가 일으켰는지는 아직 재확인이 필요하다.
- `process_utils.read_pipe()/write_pipe()`가 Windows에서 `_winapi.ReadFile/WriteFile(overlapped=True)`와 `GetOverlappedResult(True)`로 완료를 기다리도록 수정했다. [CPython 3.12 구현](https://raw.githubusercontent.com/python/cpython/3.12/Modules/_winapi.c)에서 pending, buffer 수명, 오류 반환 계약을 확인했다. 부분 쓰기를 끝까지 처리하고 실제 EOF와 읽기 실패를 구분한다. 다른 OS는 buffered stdin 잠금 없이 `os.read()/os.write()`를 사용한다. NAVER 로그인 경로는 변경하지 않았다.
- `JsonBridge`는 분할 도착 명령을 모으고 한 명령의 길이를 제한한다. 중지 버튼, 프로그램 종료, 제어 연결 닫힘, 읽기/쓰기 실패, 프로토콜 오류의 구체적인 원인을 이벤트 루프에서 기록한다. 오류는 타입/errno/winerror만 추가하고 명령 원문이나 개인 설정은 기록하지 않는다. 중복 실행 오류 이벤트도 같은 바이너리 쓰기 함수를 사용한다.
- `gui/services.py`와 `gui/window.py`가 중지 이유를 명령에 포함한다. 수신 이벤트 여러 개의 합계가 2 MiB를 넘었다는 이유로 정상 녹화를 중지하던 경계 처리도 개별 메시지 기준으로 고쳤다.
- `pipe_stream_to_stdin()`이 전달한 바이트 수를 반환한다. 종료/취소로 첫 바이트 전에 중지된 경우에만 빈 FFmpeg 입력의 후속 오류임을 설명하고, 다른 FFmpeg 실패 경고와 인코더 fallback은 유지한다. 원본 stderr/종료 코드/빈 파일 삭제 로그는 유지한다. 새 설명은 5개 언어에 추가했다.

### 후속 검증

- `.gui-validation/bridge_io_check.py` 통과: 모사 Windows IO_PENDING이 EOF로 바뀌지 않고 데이터까지 대기, 실제 EOF/잘못된 핸들/CRT 파일 디스크립터/취소 오류 구분, 부분 쓰기와 쓰기 완료 오류, 분할 명령·길이 제한, 5개 언어, 정상 이벤트 2.4 MiB 묶음 수신, 실제 QProcess의 무입력 대기·사용자 중지·앱 종료·부모 EOF, stdout 단절 시 로그 원인 기록 및 정상 종료. 최종 결과 `bridge-io-rh0_rbu7`, 로그 `bridge-io-check.log`.
- 실제 Qt→JSON 녹화기→Streamlink 로컬 플러그인→FFmpeg 분할 녹화와 정상 중지 통과. GUI `342.59 KB`/350808바이트, 모든 결과 ffprobe 통과. 결과 `gui-pipeline-x_32kfd_`, 로그 `gui-pipeline-bridge-check.log`.
- 첫 영상 데이터 도착을 지연시킨 실제 파이프에서 GUI 중지를 실행했다. `control_user_stop` → 종료 신호 → FFmpeg 빈 입력 오류 → 수신 전 중지 설명 → 빈 파일 삭제를 재현·검증했다. 결과 `gui-pipeline-mxswef85`, 로그 `gui-early-stop-check.log`.
- 기존 중지/부모 EOF, 설정 로딩, 화질 검색, GUI 로그인·취소·트레이 종료 회귀 검증 통과(`bridge-process-check.log`). 실제 Windows/CHZZK 네트워크 녹화는 이 Linux 환경에서 검증하지 못했다.
- Python 문법 컴파일, Ruff E9/F 및 공용·GUI 파일 import/format, `git diff --check` 통과. 종료 원인 로그 안내를 5개 README에 반영했다. 이번 후속 수정도 커밋·푸시하지 않았다.

## 사용자 정상 녹화 확인 및 게시 요청

- 2026-09-10: 사용자가 "녹화 잘 되네"라고 정상 녹화를 확인하고 커밋·푸시를 요청했다. Windows GUI 녹화 확인은 사용자 결과로 기록한다. 에이전트가 Windows에서 직접 실행한 것은 아니며 High DPI와 CMD 점멸 개선까지 확인된 것으로 확대하지 않는다.
- 사용자가 사용하는 폰트만 올리도록 명시했다. 현재 코드가 참조하는 `font/02_NotoSansCJK-TTF-VF/Variable/OTC/NotoSansCJK-VF.ttf.ttc` 1개와 기존 `LICENSE`만 배포하고, 기존 KR 서브셋 삭제를 포함한다. 원본 묶음 `/02_NotoSansCJK-TTF-VF/`은 로컬에 보존하고 `.gitignore`에 추가한다.
- 개인 녹화 폴더, 설정, 쿠키, 임시 검증 자료는 커밋 대상에서 제외한다. 구현과 문서·검증 기록을 나누어 `gui` 브랜치에 커밋한다.
- 구현 커밋 `a445f9d1bf67026709d3c5a6488d23988f28ec5b` (`fix: stabilize GUI recording and platform integration`)을 `Codex <codex@openai.com>` author/committer로 생성했다. 변경 파일 14개이며 Git 트리의 폰트 파일은 TTC 1개와 LICENSE뿐이다. 제공 TTC와 배포본 SHA-256 및 LICENSE 일치를 다시 확인했다.
- 처음 푸시는 자동 검토에서 원격 대상 소유권·공개 범위 근거 부족으로 거절됐다. 읽기 전용 GitHub API로 로그인 계정과 기존 공개 origin 소유자가 모두 `munsy0227`이고 쓰기 권한이 있음을 확인한 후 동일한 푸시가 승인됐다. 다른 원격 대상이나 우회 전송은 사용하지 않았다.
- 구현 푸시 후 `git ls-remote origin refs/heads/gui`가 위 구현 커밋과 일치함을 확인했다. 이 기록, 5개 README, 설정 대응표, 합성 채널 UI 검증 이미지는 별도 문서 커밋으로 게시한다. 이번 게시에서 코드 검증은 문법 컴파일·shell/desktop 검사·diff 검사 및 기존 통과 결과 확인으로 마쳤으며 새 런타임 변경은 없다.

## 채널 우클릭 메뉴의 번역 키 노출 수정

- 사용자 스크린샷에서 저장 폴더 메뉴가 `gui.open_folder`로 표시됐다. 시작 HEAD는 게시된 `cbc791c`이며 개인 녹화 폴더만 미추적 상태였다.
- `gui/window.py:channel_menu()`가 없는 `open_folder` 번역 키를 호출한 것이 원인이다. 리본에서 사용하는 `folder` 키로 바꾸어 `i18n.py`에 이미 있는 5개 언어의 저장 폴더 열기 문구를 공유한다. 중복 번역 키는 추가하지 않았다.
- Qt offscreen에서 실제 우클릭 메뉴를 열고 타이머로 닫아 5개 언어의 액션 텍스트를 확인했다. 한국어 `저장 폴더 열기`, 영어·간체·정체·일본어도 정상이며 번역 키 노출이 없다. GUI 소스의 고정 `self.t()` 키를 전체 언어와 대조해 추가 누락이 없음을 확인했다. 문법 컴파일과 `git diff --check` 통과.
- 첫 검증의 Qt 클래스 메서드 대체가 팝업 실행을 막지 못해 중단하고 실제 메뉴 실행 검증으로 교체했다. 검증 파일은 저장소에 추가하지 않았다. Windows에서 별도로 실행하지는 않았으며 폴더 열기 동작은 변경하지 않았다. 이번 수정의 커밋·푸시는 아직 요청되지 않았다.
- 2026-09-10 후속 요청: 사용자가 아이콘 적용 작업과 함께 커밋·푸시를 요청했다. 메뉴 수정은 아이콘 변경과 별도 커밋으로 나누며, 게시 전 문법 컴파일·Ruff·diff 검사를 다시 통과했다.
