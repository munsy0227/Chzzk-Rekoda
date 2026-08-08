import json
import os
import sys
import tempfile
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from i18n import language_display_name, language_options, normalize_language


CONFIG_FILE_PATH = BASE_DIR / "config.json"
DEFAULT_PROMPT_LANGUAGE = "ko"
CONFIG_REPLACE_ATTEMPTS = 5
CONFIG_REPLACE_RETRY_SECONDS = 0.2


MESSAGES = {
    "title": {
        "ko": "설치 언어를 선택하세요.",
        "en": "Select the installation language.",
        "zh-CN": "请选择安装语言。",
        "zh-TW": "請選擇安裝語言。",
        "ja": "インストール言語を選択してください。",
    },
    "prompt": {
        "ko": "언어 번호 또는 언어 코드를 입력하세요 [기본값: 1]: ",
        "en": "Enter a language number or language code [default: 1]: ",
        "zh-CN": "请输入语言编号或语言代码 [默认值：1]：",
        "zh-TW": "請輸入語言編號或語言代碼 [預設值：1]：",
        "ja": "言語番号または言語コードを入力してください [既定値: 1]: ",
    },
    "invalid": {
        "ko": "지원하지 않는 언어입니다. 다시 입력해 주세요.",
        "en": "Unsupported language. Please try again.",
        "zh-CN": "不支持的语言。请重试。",
        "zh-TW": "不支援的語言。請再試一次。",
        "ja": "対応していない言語です。もう一度入力してください。",
    },
    "saved": {
        "ko": "설치 언어가 {language}(으)로 저장되었습니다.",
        "en": "Installation language saved as {language}.",
        "zh-CN": "安装语言已保存为 {language}。",
        "zh-TW": "安裝語言已儲存為 {language}。",
        "ja": "インストール言語を {language} として保存しました。",
    },
}


KOREAN_ALIASES = {"ko", "kr", "kor", "korean", "한국어"}


def message(locale, key, **kwargs):
    text = MESSAGES[key][normalize_language(locale)]
    return text.format(**kwargs)


def read_config():
    if not CONFIG_FILE_PATH.exists():
        return {}
    try:
        with CONFIG_FILE_PATH.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}
    return config if isinstance(config, dict) else {}


def save_config(config):
    fd = None
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix="config.",
            suffix=".tmp",
            dir=BASE_DIR,
            text=True,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            fd = None
            json.dump(config, file, indent=2, ensure_ascii=False)
            file.write("\n")
        for attempt in range(CONFIG_REPLACE_ATTEMPTS):
            try:
                os.replace(temp_path, CONFIG_FILE_PATH)
                temp_path = None
                break
            except PermissionError:
                if attempt == CONFIG_REPLACE_ATTEMPTS - 1:
                    with CONFIG_FILE_PATH.open("w", encoding="utf-8") as file:
                        json.dump(config, file, indent=2, ensure_ascii=False)
                        file.write("\n")
                        file.flush()
                        os.fsync(file.fileno())
                    break
                time.sleep(CONFIG_REPLACE_RETRY_SECONDS)
        if os.name != "nt":
            try:
                os.chmod(CONFIG_FILE_PATH, 0o600)
            except OSError:
                pass
    finally:
        if fd is not None:
            os.close(fd)
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def select_language(raw_value):
    value = raw_value.strip()
    options = language_options()
    if not value:
        return options[0][0]
    if value.isdigit():
        index = int(value) - 1
        if 0 <= index < len(options):
            return options[index][0]
        return None

    normalized = normalize_language(value)
    if normalized != "ko" or value.lower() in KOREAN_ALIASES:
        return normalized
    return None


def main():
    config = read_config()
    prompt_language = normalize_language(
        config.get("language", DEFAULT_PROMPT_LANGUAGE)
    )

    print(message(prompt_language, "title"))
    for index, (code, name) in enumerate(language_options(), start=1):
        print(f"{index}. {name} ({code})")

    while True:
        selected = select_language(input(message(prompt_language, "prompt")))
        if selected is None:
            print(message(prompt_language, "invalid"))
            continue
        config["language"] = selected
        save_config(config)
        print(
            message(
                selected,
                "saved",
                language=language_display_name(selected),
            )
        )
        return


if __name__ == "__main__":
    main()
