# GUI 후속 개선과 채널별 녹화 옵션

## 요청과 범위

- 2026-09-08: 쿠키 가져오기 수정, 방송 제목 열, 채널별 분할, 직접/사용자 화질 및 FPS, 우클릭 메뉴, 지정 Noto Sans KR 폰트, H.264, 백그라운드/트레이, 원본 제목 TXT의 9개 항목을 요청받았다.
- `gui` 브랜치, 구현 기준 HEAD `3ca8e78`. 기존 사용자 `아리사/`와 개인 설정은 변경하지 않았다.
- 2026-09-09: 계속 요청에 따라 마지막 회귀 검증과 문서/화면 정리까지 완료했다.
- 2026-09-09: 사용자가 이번 변경의 커밋과 `gui` 브랜치 푸시를 명시적으로 요청했다. 제공된 폰트 묶음에서는 GUI가 실제 사용하는 `Variable/TTF/Subset/NotoSansKR-VF.ttf`와 배포 `LICENSE`만 포함한다. 나머지 폰트 및 개인 녹화 폴더는 커밋 대상에서 제외한다.

## 구현과 결정

- `browser_login.py`: 현재 문서의 쿠키만 재조회하던 경로를 개선했다. Chromium은 새 브라우저 세션의 `Storage.getCookies`, Firefox/대체 경로는 열린 NAVER 탭의 HttpOnly 쿠키를 읽는다. NAVER 도메인과 NID_AUT/NID_SES만 허용하고 로그인 성공 시점의 스냅샷을 반환한다. 페이지 로딩 시간 초과를 쿠키 실패로 단정하지 않으며 브라우저/드라이버/닫힌 창/인증 대기 시간 초과/취소를 값 없이 구분한다. 로그인 중 stdout 진단 출력은 프로토콜과 분리한다.
- `gui/settings_dialog.py`: JSON 행 파싱, 중복 종료 콜백 방지, 시작 중 취소 전달, 실패 이유 표시를 보완했다. 실제 사용자 실패 환경/오류 문구는 질문했으나 아직 답변을 받지 못했다.
- `recording_options.py`: `quality_settings={mode,width,height,fps}`, 실제 Streamlink 화질 목록 기반 선택, 크기/FPS 필터 결합, 채널별 분할 상속을 공용화했다. FPS 0은 원본, 사용자 크기는 짝수, width 0은 원본 비율이다. 같은 해상도 우선, 없으면 가까운 상위 화질/최고 화질에서 변환한다.
- `config_store.py`: 전역/채널 `quality_settings`, 채널 `recording_split_minutes`(없음/null=전역, 0=끄기), `h264_settings`, `gui_settings.close_to_tray`를 정규화한다. 기존 설정은 기본값으로 마이그레이션한다. H.264/HEVC/AV1은 상호 배타다.
- `encoding_h264.py`, `chzzk_record.py`: 6종 H.264 인코더 인수와 실제 FFmpeg probe, 하드웨어 실패 시 libx264 fallback. 직접 화질은 스트림 복사, FPS/해상도 변경 시 선택 코덱 또는 기본 H.264(WebM=VP9) 인코딩. 명시적 H.264+WebM은 MKV로 전환한다. Streamlink는 같은 Python 환경에서 실행하며 화질 조회 프로세스는 30초/2MiB 제한 및 종료 정리를 갖는다.
- `chzzk_record.py:save_original_title()`: 최종/불완전 영상과 각 분할 파일 옆에 UTF-8 원본 제목 TXT를 저장한다. 영상 파일명의 축약/해시는 유지한다. GUI에는 파일명용 정제 전 제목을 전달한다.
- `gui/recording_controls.py`: 전역/채널 화질 및 채널별 분할 편집기를 공유한다. `settings.py`의 메인 메뉴 10/11과 채널 메뉴 5에도 새 설정을 연결했다.
- `gui/window.py`: 채널-방송 제목-상태 순서, 원본 제목 툴팁, 우클릭한 행의 설정/등록 해제/폴더/활성화. 닫기 시 트레이 유지 옵션(기본 켜짐), 복원/시작/중지/안전 종료 메뉴. 트레이가 없는 데스크톱은 숨겨진 채로 남지 않도록 기존 안전 종료를 사용한다.
- `gui/appearance.py`: 제공된 `font/NotoSansKR-VariableFont_wght.ttf`를 우선 로드한다. Qt가 기본 인스턴스를 Thin으로 식별하므로 가변 wght=400을 명시했다. 창/트레이용 아이콘도 제공한다. 9월 9일 계속 작업 시 사용자의 폰트 폴더가 Noto CJK 배포본으로 바뀌고 기존 TTF/OFL.txt가 사라진 것을 확인했다. 새 파일은 변경하지 않고 `font` 아래 `NotoSansKR-VF.ttf`, `NotoSansCJKkr-VF.ttf` 순으로 탐색하는 대체 경로를 추가했다. 현재 라이선스는 `font/02_NotoSansCJK-TTF-VF/LICENSE`다.
- 사용자 문구는 `i18n.py` 5개 언어와 README 5개 언어에 반영했다.

## 확인한 검증

- Python 문법 컴파일과 변경 Python의 Ruff E9/F 통과. 신규/분리 모듈 import 정리 및 포맷 적용.
- `.gui-validation/enhancements_check.py`: 직접 화질 5종, FPS만 변환, 사용자 크기, 누락 화질 대체, VAAPI 필터 결합, 채널별 분할 상속/끄기, 6종 H.264 probe와 CPU 성공 확인. CLI 저장, 5개 언어 폼, 코덱 상호 배타, 프리셋, 폰트, 원본 제목 열, 실제 우클릭 메뉴의 대상 행, 모의 트레이 환경의 숨기기/복원/안전 종료 통과.
- 쿠키는 합성 데이터로 도메인 필터, Chromium CDP, 다른 탭, 페이지 시간 초과, 성공/실패 시 브라우저 정리를 확인했다. `.gui-validation/browser_check.py`는 실제 Firefox의 임시 프로필과 로컬 서버에서 합성 HttpOnly 쿠키, 다른 탭, 현재 탭을 닫은 뒤 수집까지 통과했다. 실제 계정은 사용하지 않았다. Firefox에도 CDP 메서드가 노출되지만 호출은 실패함을 확인해 브라우저 capabilities로 Chromium만 사용하게 했다.
- 공개 방송에서 쿠키 없이 실제 Streamlink 목록 `144p, 360p, 480p, 720p60, 1080p60, worst, best` 조회 성공. 개인 설정은 별도 검증 설정으로 대체했다.
- `.gui-validation/encoding_check.py`: 합성 입력을 실제 녹화 파이프에 넣어 직접 화질 5종의 복사, 720p60→720p30의 FPS 단독 변환, 960×540/24FPS, H.264+WebM→MKV, 사용자 WebM/VP9를 FFmpeg/ffprobe로 확인했다.
- 채널별 분할 켜기와 전역 분할을 채널에서 끄는 경로도 통과했다. 분할 테스트만 간격을 2초로 가속했다. 마지막 1프레임 TS는 FPS를 추론할 타임스탬프가 부족하므로 디코딩/크기를 확인하고 FPS는 여러 프레임을 가진 세그먼트에서 확인한다.
- 모든 보존 영상/세그먼트에서 긴 한글·이모지·개행·특수문자를 포함한 원본 제목이 TXT와 완전히 일치했고 파일명은 255바이트 이하였다.
- 제목 TXT의 다중 이름 충돌, 이미 존재하는 비 UTF-8 메모, CRLF 원문, 중복 저장을 추가 확인했다. 충돌 후보마다 이름을 축약해 255바이트 제한을 지키고 기존 메모는 보존한다.
- 5개 언어의 900px 설정 리본에서 버튼이 창 밖으로 넘치지 않음을 확인했다. 폰트 굵기와 화질 폼을 화면으로 점검했다.
- 교체된 Noto CJK 배포본의 한국어 폰트 로드 후 GUI 회귀 검증과 화면 확인을 다시 통과했다. uvloop의 조각 JSON 화질 조회도 10회 연속 통과했다. 최종 Python 컴파일, Ruff E9/F 및 공용/GUI 모듈 import·포맷 검사, `git diff --check`, `.ai` 문서 링크를 확인했다.
- `.gui-validation/process_options_check.py`: 실제 녹화 프로세스의 JSON 중지와 부모 stdin EOF, 확장 설정 반환, 여러 조각으로 들어오는 화질 JSON, GUI 로그인 프로세스의 진단 stdout/분류 오류/시작 직후 취소, 로그인 대화상자에서 트레이 안전 종료까지 통과했다. Linux 녹화기와 같은 uvloop로 확인했다. 검증용 기본 asyncio selector 환경에서는 짧은 자식 프로세스의 `wait()`가 간헐적으로 시간 초과했으며 실제 uvloop 경로에서는 재현되지 않았다.
- 화면 캡처: [방송 제목 열](../assets/qt-gui-title-column.png), [채널별 설정](../assets/qt-gui-channel-options.png), [전체 화질 설정](../assets/qt-gui-quality-options.png). 검증용 합성 채널/상태이며 실제 방송 화면으로 표현하지 않는다.

## 완료 상태와 한계

- 9개 요청의 코드 구현, 공용 CLI/GUI 설정 연결, 다국어/README 및 `.ai` 기록을 완료했다. 9월 9일 요청에 따른 커밋/푸시 결과는 아래 게시 기록으로 갱신한다.
- 실제 NAVER 계정 로그인, Windows/macOS의 네이티브 트레이, 장시간 실방송, 실제 GPU 인코딩은 미검증이다.

## 참고

- [Selenium 쿠키](https://www.selenium.dev/documentation/webdriver/interactions/cookies/), [Streamlink CLI](https://streamlink.github.io/cli.html), [Qt 트레이](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html), [FFmpeg 필터](https://ffmpeg.org/ffmpeg-filters.html).
- [Noto Sans KR 공식 라이선스](https://raw.githubusercontent.com/google/fonts/main/ofl/notosanskr/OFL.txt).
