"""
HTTP / JS-render fetcher.

Order of preference:
  1. httpx (or requests) for JSON / static HTML
  2. Playwright for JS-rendered pages (preferred browser automation)
  3. Selenium as fallback

Never executes remote page scripts inside our process except via
headless browser isolation (Playwright/Selenium). HTML returned to
parsers is treated as untrusted text and sanitized by parsers.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .allowlist import assert_allowed_url

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


def _ua() -> str:
    return random.choice(USER_AGENTS)


@dataclass
class FetchResult:
    url: str
    status: int
    body: str
    content_type: str = ""
    final_url: str = ""
    engine: str = "http"
    binary: Optional[bytes] = None
    json_data: Any = None


def _default_headers(referer: Optional[str] = None) -> Dict[str, str]:
    h = {
        "User-Agent": _ua(),
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
    }
    if referer:
        h["Referer"] = referer
        try:
            origin = f"{urlparse(referer).scheme}://{urlparse(referer).netloc}"
            h["Origin"] = origin
        except Exception:
            pass
    return h


def http_get(
    url: str,
    *,
    timeout: float = 35.0,
    retries: int = 3,
    referer: Optional[str] = None,
) -> FetchResult:
    url = assert_allowed_url(url)
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            return _http_request("GET", url, timeout=timeout, referer=referer)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("GET attempt %s failed for %s: %s", attempt, url, exc)
            time.sleep(min(2 ** attempt, 8) + random.random())
    raise RuntimeError(f"Network failure fetching {url}: {last_err}")


def http_post_json(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout: float = 40.0,
    retries: int = 3,
    referer: Optional[str] = None,
) -> FetchResult:
    url = assert_allowed_url(url)
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            return _http_request(
                "POST",
                url,
                timeout=timeout,
                referer=referer,
                json_body=payload,
            )
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("POST attempt %s failed for %s: %s", attempt, url, exc)
            time.sleep(min(2 ** attempt, 8) + random.random())
    raise RuntimeError(f"Network failure posting {url}: {last_err}")


def _http_request(
    method: str,
    url: str,
    *,
    timeout: float,
    referer: Optional[str],
    json_body: Optional[Dict[str, Any]] = None,
) -> FetchResult:
    headers = _default_headers(referer)
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json, text/plain, */*"

    # Prefer httpx
    try:
        import httpx  # type: ignore

        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            if method == "GET":
                r = client.get(url)
            else:
                r = client.post(url, json=json_body)
            final = str(r.url)
            assert_allowed_url(final.split("?")[0] if "://" in final else url)
            ctype = r.headers.get("content-type", "")
            text = r.text
            data = None
            if "json" in ctype.lower() or text[:1] in ("{", "["):
                try:
                    data = r.json()
                except Exception:
                    data = None
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code} for {url}")
            return FetchResult(
                url=url,
                status=r.status_code,
                body=text,
                content_type=ctype,
                final_url=final,
                engine="httpx",
                binary=r.content,
                json_data=data,
            )
    except ImportError:
        pass

    # Fallback: requests
    try:
        import requests  # type: ignore

        if method == "GET":
            r = requests.get(url, headers=headers, timeout=timeout)
        else:
            r = requests.post(url, headers=headers, json=json_body, timeout=timeout)
        final = r.url
        assert_allowed_url(final.split("?")[0] if "://" in final else url)
        ctype = r.headers.get("content-type", "")
        text = r.text
        data = None
        try:
            data = r.json()
        except Exception:
            data = None
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code} for {url}")
        return FetchResult(
            url=url,
            status=r.status_code,
            body=text,
            content_type=ctype,
            final_url=final,
            engine="requests",
            binary=r.content,
            json_data=data,
        )
    except ImportError as exc:
        raise RuntimeError("Install httpx or requests to fetch promotion pages") from exc


def fetch_rendered_html(
    url: str,
    *,
    timeout_ms: int = 45000,
    wait_selector: Optional[str] = None,
    wait_ms: int = 2500,
) -> FetchResult:
    """
    Load a JS-rendered page. Playwright preferred, Selenium fallback.
    Still enforces allowlist on the navigation URL.
    """
    url = assert_allowed_url(url)
    try:
        return _playwright_fetch(url, timeout_ms=timeout_ms, wait_selector=wait_selector, wait_ms=wait_ms)
    except Exception as pw_err:  # noqa: BLE001
        logger.warning("Playwright failed (%s); trying Selenium", pw_err)
        try:
            return _selenium_fetch(url, timeout_ms=timeout_ms, wait_selector=wait_selector, wait_ms=wait_ms)
        except Exception as se_err:  # noqa: BLE001
            raise RuntimeError(
                f"JS rendering failure for {url}. Playwright: {pw_err}; Selenium: {se_err}"
            ) from se_err


def _playwright_fetch(
    url: str,
    *,
    timeout_ms: int,
    wait_selector: Optional[str],
    wait_ms: int,
) -> FetchResult:
    from playwright.sync_api import sync_playwright  # type: ignore

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=_ua(), java_script_enabled=True)
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=min(timeout_ms, 20000))
                except Exception:
                    pass
            if wait_ms:
                page.wait_for_timeout(wait_ms)
            final = page.url
            assert_allowed_url(final.split("#")[0])
            html = page.content()
            return FetchResult(
                url=url,
                status=200,
                body=html,
                content_type="text/html",
                final_url=final,
                engine="playwright",
            )
        finally:
            browser.close()


def _selenium_fetch(
    url: str,
    *,
    timeout_ms: int,
    wait_selector: Optional[str],
    wait_ms: int,
) -> FetchResult:
    from selenium import webdriver  # type: ignore
    from selenium.webdriver.chrome.options import Options  # type: ignore
    from selenium.webdriver.common.by import By  # type: ignore
    from selenium.webdriver.support import expected_conditions as EC  # type: ignore
    from selenium.webdriver.support.ui import WebDriverWait  # type: ignore

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument(f"--user-agent={_ua()}")
    driver = webdriver.Chrome(options=opts)
    try:
        driver.set_page_load_timeout(max(10, timeout_ms // 1000))
        driver.get(url)
        if wait_selector:
            try:
                WebDriverWait(driver, min(20, timeout_ms // 1000)).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            except Exception:
                pass
        if wait_ms:
            time.sleep(wait_ms / 1000.0)
        final = driver.current_url
        assert_allowed_url(final.split("#")[0])
        html = driver.page_source
        return FetchResult(
            url=url,
            status=200,
            body=html,
            content_type="text/html",
            final_url=final,
            engine="selenium",
        )
    finally:
        driver.quit()
