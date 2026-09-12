# 빈 툴팁, 작은 창 미리보기 및 TTC 폰트 적용

확인일: 2026-09-11. 기존 `gui` 브랜치의 미커밋 녹화 중지·화질 수정은 그대로 보존했다.

## 사용자 요청

- 빈 방송 제목에 포인터를 올리면 빈 상자가 표시된다.
- Debian 13 KDE Plasma에서 작은 창의 미리보기 스트리머 이름이 영상에 가려진다. Windows에서는 해당 현상이 없다는 사용자 설명이다.
- GUI가 간헐적으로 시스템 폰트로 시작한다. 전체 글자를 더 굵게 한다.

## 확인과 변경

- `gui/window.py:update_rows()`와 `gui/common.py:ElidedLabel.setText()`가 빈 내용도 `<qt></qt>`로 감싸고 있었다. 공용 `text_tooltip()`으로 비어 있거나 공백뿐인 내용에는 툴팁을 지우고, 실제 제목은 기존처럼 HTML 이스케이프 및 줄바꿈을 보존한다.
- `ElidedLabel`의 최소 높이를 실제 QLabel 힌트/글꼴 높이와 일치시키고 FontChange/StyleChange 때 생략 문자열 및 레이아웃 힌트를 갱신한다. 긴 내용의 가로 생략/전체 툴팁은 유지한다.
- 영상 QLabel은 명시적 최소 크기 240×135를 유지하면서 pixmap 자체 크기는 레이아웃 계산에서 무시한다. 창 전체 Resize 대신 영상 위젯의 실제 Resize 시점에 프레임을 다시 맞춰 큰 프레임이 작은 창의 캡션 공간을 밀지 않게 한다.
- 수정 전 Debian 13.6/Qt 6.11.2 offscreen에서 `apply_application_font()` 후에도 창 스타일 적용 시 실제 QLabel/QTableWidget 폰트가 시스템 `Noto Sans` 9pt/400으로 확인됐다. 앱 setFont와 QSS 조합 대신 앱 전체 QSS에서 family/10pt/500을 명시한다. `chzzk_gui.main()`도 창 생성 전에 TTC를 등록/적용하며 실패 결과를 영구 캐시하지 않는다.
- Linux의 설치된 정적 `Noto Sans CJK [GOOG]`와 제공 TTC `[ADBO]`가 같은 family를 공유했다. 등록된 family와 TTC OS/2 vendor를 사용해 Qt가 구분 가능한 경우 제공 TTC 이름을 우선한다. 다른 플랫폼에서 foundry 이름이 없으면 등록된 기본 이름을 사용한다.
- 제공 TTC가 Qt/FreeType에서 Thin face로 노출되어 QSS 굵기만 바꿔도 실제 획이 얇게 남을 수 있었다. `VariableFontWeights`는 FontChange/Polish 때 해당 위젯의 최종 weight를 가변 wght 축에 맞춘다. 본문 500, 제목 QLabel 600을 사용하며 기존 full hinting/antialias, Windows DirectWrite 및 DPI 옵션은 유지한다.
- 폰트 파일 자체, CLI, 설정 파일 형식, 녹화 엔진 및 번역 문구는 이번 변경에서 수정하지 않았다.

## 검증 결과

- `.gui-validation/font_layout_check.py`의 임시 설정/합성 프레임 검사 통과. 실패한 폰트 등록 후 재시도, 5개 언어 × 760×600/1180×820/1400×900 및 반복 축소, 영상 있음/없음, 긴 제목 생략/이스케이프, 빈 제목 HelpEvent에서 실제 QToolTip 숨김을 확인했다.
- 모든 언어에서 본문/제목의 QFontInfo family, QRawFont의 fvar 테이블, 한국어·중국어·일본어·영문 글리프 지원, 최종 굵기와 wght 축을 확인했다. 시스템 기본 폰트를 20pt DejaVu로 바꿔도 앱 위젯의 제공 TTC/10pt/굵기는 유지됐다.
- 작은 창에서 영상/제목/안내문이 세로로 겹치지 않고 제목 높이가 실제 글꼴 높이 이상인지 확인했다. 이전 큰 프레임을 가진 상태에서 축소한 후 pixmap이 새 영상 영역 안에 들어가는지 확인했다.
- 설정 창, 첫 실행 마법사의 일본어 전환, 밝은/어두운 팔레트 전환 검증 통과. 원래 임시 설정 파일의 바이트가 동일함을 확인했다.
- 기본/150%/200% 배율 검사 통과. 최종 캡처는 각각 `.gui-validation/font-layout-check-da6rwjpo/`, `font-layout-check-tqfeakp0/`, `font-layout-check-o9zxka4m/`. `ko-final.png`, `ja-760-frame.png`, `settings.png`, `dark.png` 등을 생성했다. 앞선 QT_FONT_DPI=144 검사도 통과했다.
- 400/500/600 굵기에서 같은 문자열을 실제 QImage로 렌더한 획 농도 합이 346413/428611/474907로 증가해 실제 굵기 반영을 확인했다. 최종 한국어 작은 창, 일본어 프레임, 설정 화면을 시각 점검했다.
- 변경 Python 컴파일, GUI 파일 Ruff E9/F/I 및 포맷 검사, `git diff --check` 통과. 앞선 중지 상태/화질 변경 파일도 함께 문법 컴파일했다. 해당 녹화 동작의 실행 검증은 [직전 작업 기록](2026-09-11-stop-status-quality.md)에 있다.
- 임시 검사·캡처는 Git 제외 경로에만 있으며 사용자 설정/쿠키/기존 녹화는 수정하지 않았다. 초기 구현 단계에서는 커밋/푸시를 수행하지 않았다.

## 근거와 검증 범위

- [Qt QApplication.setFont](https://doc.qt.io/qt-6/qapplication.html#setFont): 애플리케이션 폰트와 스타일시트 조합 주의.
- [Qt QFont](https://doc.qt.io/qt-6/qfont.html#setVariableAxis): 가변 축 적용과 Windows GDI 제한. DirectWrite 옵션은 유지한다.
- [Qt 스타일시트 상속](https://doc.qt.io/qt-6/stylesheet-syntax.html#inheritance), [QLabel sizeHint](https://doc.qt.io/qt-6/qlabel.html#sizeHint).
- [OpenType OS/2 vendor](https://learn.microsoft.com/en-us/typography/opentype/spec/os2#achvendid): 제공 TTC의 vendor와 설치 폰트를 구분하는 근거.
- 실제 Debian 13 KDE 데스크톱 세션, Windows/macOS 실환경은 직접 실행하지 않았다. 이번 화면 검증은 Debian 13.6의 Qt offscreen이며 시스템 폰트/팔레트 변경을 모사했다.

## 커밋·푸시 요청

- 2026-09-11 사용자가 커밋·푸시를 명시적으로 요청했다. 녹화 처리 수정과 분리해 GUI 코드 4개(`chzzk_gui.py`, `gui/appearance.py`, `gui/common.py`, `gui/window.py`), 이 기록과 `.ai/KNOWLEDGE.md`를 `fix: stabilize GUI fonts and compact preview layout`로 묶는다.
- 게시 직전 Python 컴파일, Ruff E9/F/I 및 포맷 검사, `git diff --check`를 다시 통과했다. 앞선 5개 언어·100/150/200% 배율 검증 이후 GUI 동작 변경은 없다.
- 대상은 기존 `origin/gui`이며 author/committer는 기존 관례의 `Codex <codex@openai.com>`을 사용한다. 실제 사용하는 TTC 한 개와 LICENSE만 추적 중임을 확인했고, 추가 폰트 파일이나 개인 설정·녹화·검사 산출물은 포함하지 않는다.
