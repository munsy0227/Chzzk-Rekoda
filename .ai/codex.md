# Codex Notes

- 기본 응답 언어는 한국어로 한다.
- 이 저장소는 CHZZK 자동 녹화 프로그램이며, 실행 진입점은 `chzzk_record.py`와 `settings.py`다.
- 사용자에게 보이는 문자열을 추가하거나 수정할 때는 다국어 지원도 함께 갱신한다.
  - 런타임/설정/설치 메시지는 `i18n.py`의 한국어, 영어, 중국어 간체, 중국어 정체, 일본어 번역을 같이 수정한다.
  - 문서 문구는 `README.md`, `README.en.md`, `README.zh-CN.md`, `README.zh-TW.md`, `README.ja.md`를 같이 확인한다.
- Python 파일을 수정한 뒤에는 최소한 `python3 -m py_compile`로 문법을 확인하고, 가능하면 `git diff --check`를 실행한다.
