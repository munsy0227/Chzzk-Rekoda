"""Isolated browser login worker. Cookie values go only to its private pipe."""

import json
import sys
import threading
import time

from config_store import AUTH_COOKIE_NAMES, NAVER_LOGIN_URL, sanitize_cookie


def collect_browser_cookies(browser, wait_for_login):
    from selenium import webdriver

    factories = {
        "chrome": webdriver.Chrome,
        "edge": webdriver.Edge,
        "firefox": webdriver.Firefox,
    }
    driver = None
    try:
        driver = factories[browser]()
        driver.set_page_load_timeout(30)
        driver.get(NAVER_LOGIN_URL)
        wait_for_login(driver)
        return {
            cookie["name"]: sanitize_cookie(cookie.get("value"))
            for cookie in driver.get_cookies()
            if cookie.get("name") in AUTH_COOKIE_NAMES
        }
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def main():
    cancel = threading.Event()

    def commands():
        # Explicit cancellation or parent pipe closure cancels only our browser.
        sys.stdin.buffer.readline(4096)
        cancel.set()

    threading.Thread(target=commands, daemon=True).start()

    def wait(driver):
        deadline = time.monotonic() + 180
        while not cancel.wait(1):
            cookies = {c["name"]: c.get("value") for c in driver.get_cookies()}
            if all(cookies.get(name) for name in AUTH_COOKIE_NAMES):
                return
            if time.monotonic() > deadline:
                break
        raise TimeoutError()

    try:
        cookies = collect_browser_cookies(sys.argv[1], wait)
        if not all(cookies.get(name) for name in AUTH_COOKIE_NAMES):
            raise ValueError()
        print(json.dumps({"cookies": cookies}), flush=True)
        return 0
    except Exception:
        # Driver errors can contain sensitive URLs; never forward their text.
        print(json.dumps({"error": "login_failed"}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
