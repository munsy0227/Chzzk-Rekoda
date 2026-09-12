"""Isolated browser login worker. Cookie values go only to its private pipe."""

import contextlib
import json
import os
import sys
import threading
import time
from urllib.parse import urlparse

from config_store import AUTH_COOKIE_NAMES, NAVER_LOGIN_URL, sanitize_cookie


class LoginFailure(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def failure_reason(error):
    if isinstance(error, LoginFailure):
        return error.reason
    if isinstance(error, (KeyboardInterrupt, EOFError)):
        return "login_cancelled"
    return {
        "NoSuchDriverException": "login_driver_missing",
        "SessionNotCreatedException": "login_browser_failed",
        "NoSuchWindowException": "login_window_closed",
        "InvalidSessionIdException": "login_window_closed",
    }.get(type(error).__name__, "login_failed")


def naver_cookies(cookies):
    result = {}
    for cookie in cookies:
        domain = str(cookie.get("domain", "")).lstrip(".").lower()
        if domain != "naver.com" and not domain.endswith(".naver.com"):
            continue
        name = cookie.get("name")
        if name in AUTH_COOKIE_NAMES and cookie.get("value"):
            result[name] = sanitize_cookie(cookie["value"])
    return result


def read_auth_cookies(driver):
    from selenium.common.exceptions import NoSuchWindowException, WebDriverException

    # Chromium's browser cookie store includes HttpOnly cookies even after a
    # login redirect changes the current domain or a popup becomes active.
    browser_name = getattr(driver, "capabilities", {}).get("browserName", "").lower()
    if browser_name in {"chrome", "chromium", "msedge", "microsoftedge"} and callable(
        getattr(driver, "execute_cdp_cmd", None)
    ):
        with contextlib.suppress(WebDriverException):
            cookies = naver_cookies(
                driver.execute_cdp_cmd("Storage.getCookies", {}).get("cookies", [])
            )
            if all(cookies.get(name) for name in AUTH_COOKIE_NAMES):
                return cookies
    cookies = {}
    handles = driver.window_handles
    if not handles:
        raise NoSuchWindowException()
    original = None
    with contextlib.suppress(NoSuchWindowException):
        original = driver.current_window_handle
    for handle in handles:
        try:
            driver.switch_to.window(handle)
            driver.switch_to.default_content()
            host = urlparse(driver.current_url).hostname or ""
            if host == "naver.com" or host.endswith(".naver.com"):
                cookies.update(naver_cookies(driver.get_cookies()))
        except NoSuchWindowException:
            # A popup may close between enumerating and selecting its handle.
            continue
    if original is not None:
        with contextlib.suppress(NoSuchWindowException):
            driver.switch_to.window(original)
    return cookies


def collect_browser_cookies(browser, wait_for_login):
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException

    factories = {
        "chrome": webdriver.Chrome,
        "edge": webdriver.Edge,
        "firefox": webdriver.Firefox,
    }
    driver = None
    try:
        options = {
            "chrome": webdriver.ChromeOptions,
            "edge": webdriver.EdgeOptions,
            "firefox": webdriver.FirefoxOptions,
        }[browser]()
        options.page_load_strategy = "eager"
        driver = factories[browser](options=options)
        driver.set_page_load_timeout(30)
        # A slow ad/subresource must not discard an already usable login page.
        with contextlib.suppress(TimeoutException):
            driver.get(NAVER_LOGIN_URL)
        cookies = wait_for_login(driver)
        # Keep the successful snapshot instead of rereading a redirected tab.
        return cookies if isinstance(cookies, dict) else read_auth_cookies(driver)
    finally:
        if driver is not None:
            with contextlib.suppress(WebDriverException):
                driver.quit()


def main():
    cancel = threading.Event()

    def commands():
        # Explicit cancellation or parent pipe closure cancels only our browser.
        os.read(sys.stdin.fileno(), 4096)
        cancel.set()

    threading.Thread(target=commands, daemon=True).start()

    def wait(driver):
        deadline = time.monotonic() + 180
        while not cancel.wait(1):
            cookies = read_auth_cookies(driver)
            if all(cookies.get(name) for name in AUTH_COOKIE_NAMES):
                return cookies
            if time.monotonic() > deadline:
                break
        raise LoginFailure("login_cancelled" if cancel.is_set() else "login_timeout")

    try:
        # Driver libraries sometimes print diagnostics to stdout on Windows.
        # Only our final JSON response belongs on the private protocol pipe.
        with contextlib.redirect_stdout(sys.stderr):
            cookies = collect_browser_cookies(sys.argv[1], wait)
        if not all(cookies.get(name) for name in AUTH_COOKIE_NAMES):
            raise ValueError()
        print(json.dumps({"cookies": cookies}), flush=True)
        return 0
    except Exception as error:  # noqa: BLE001 -- protocol boundary hides sensitive driver diagnostics
        # Driver errors can contain sensitive URLs; never forward their text.
        reason = failure_reason(error)
        print(json.dumps({"error": reason}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
