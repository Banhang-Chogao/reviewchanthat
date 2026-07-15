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
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .allowlist import assert_allowed_url

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Semantic patterns for "load more" style controls (language-agnostic-ish)
LOAD_MORE_RE = re.compile(
    r"(load\s*more|show\s*more|see\s*more|view\s*more|xem\s*thêm|tải\s*thêm|hiển\s*thị\s*thêm|more\s*offers|thêm\s*ưu\s*đãi)",
    re.I,
)

DETAIL_HREF_RE = re.compile(
    r"/visa-offers-and-perks/([^/?#]+)/(\d+)",
    re.I,
)


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


@dataclass
class ListingLink:
    detail_url: str
    source_id: str = ""
    slug: str = ""
    merchant: str = ""
    title: str = ""


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
            context = browser.new_context(
                user_agent=_ua(),
                java_script_enabled=True,
                locale="vi-VN",
            )
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


# ── Full browser session (Playwright primary, Selenium fallback) ─────────────


@dataclass
class BrowserCrawlSession:
    """
    Long-lived browser session for listing scroll + detail page visits.
    Prefer Playwright; fall back to Selenium for the whole session if Playwright fails at open.
    """

    engine: str = ""
    log: Callable[[str], None] = field(default=lambda _m: None)
    _impl: Any = field(default=None, repr=False)

    def __enter__(self) -> "BrowserCrawlSession":
        self._impl = _open_browser_impl(self.log)
        self.engine = self._impl.engine
        self.log(f"Browser session opened ({self.engine})")
        return self

    def __exit__(self, *args: Any) -> None:
        if self._impl:
            try:
                self._impl.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Browser close error: %s", exc)
            self._impl = None
            self.log("Browser session closed")

    def goto(self, url: str, *, timeout_ms: int = 90000) -> str:
        url = assert_allowed_url(url)
        self.log(f"Navigate → {url}")
        final = self._impl.goto(url, timeout_ms=timeout_ms)
        assert_allowed_url(final.split("#")[0].split("?")[0] if "://" in final else url)
        self.log(f"networkidle reached · final={final}")
        return final

    def wait_for_promotion_cards(self, *, timeout_ms: int = 30000) -> int:
        """Wait until at least one promotion detail link is present."""
        self.log("Waiting for promotion cards to render…")
        n = self._impl.wait_for_promo_links(timeout_ms=timeout_ms)
        self.log(f"Promotion cards visible (link count≈{n})")
        return n

    def auto_scroll_until_stable(
        self,
        *,
        max_rounds: int = 40,
        pause_ms: int = 800,
        stable_rounds: int = 3,
    ) -> int:
        """
        Scroll to bottom + click Load/Show More until no new promotion links appear.
        Returns unique detail-link count.
        """
        self.log("Auto-scroll + Load More until exhausted…")
        prev = -1
        stable = 0
        count = 0
        for i in range(max_rounds):
            self._impl.click_load_more()
            self._impl.scroll_to_bottom()
            self._impl.wait_ms(pause_ms)
            count = self._impl.count_promo_links()
            self.log(f"Scroll round {i + 1}: {count} promotion links")
            if count == prev:
                stable += 1
                if stable >= stable_rounds:
                    break
            else:
                stable = 0
            prev = count
        self.log(f"Scroll complete · {count} promotion links")
        return count

    def collect_listing_links(self, listing_url: str) -> List[ListingLink]:
        raw = self._impl.collect_promo_links()
        origin = f"{urlparse(listing_url).scheme}://{urlparse(listing_url).netloc}"
        out: List[ListingLink] = []
        seen: set[str] = set()
        for item in raw:
            href = (item.get("href") or "").strip()
            title = (item.get("title") or "").strip()
            if not href:
                continue
            if href.startswith("/"):
                href = origin + href
            if not href.startswith("https://"):
                continue
            try:
                assert_allowed_url(href.split("?")[0])
            except Exception:
                continue
            m = DETAIL_HREF_RE.search(href)
            if not m:
                continue
            slug, oid = m.group(1), m.group(2)
            if oid in seen:
                continue
            seen.add(oid)
            merchant = title or slug.replace("-", " ").strip().title()
            # Prefer slug-derived merchant when title is noisy
            if not title or len(title) < 2:
                merchant = slug.replace("-", " ").strip().title()
            clean = href.split("?")[0].split("#")[0]
            out.append(
                ListingLink(
                    detail_url=clean,
                    source_id=oid,
                    slug=slug,
                    merchant=merchant,
                    title=title or merchant,
                )
            )
        self.log(f"Collected {len(out)} unique listing promotion cards")
        return out

    def page_text_and_html(self) -> Tuple[str, str]:
        return self._impl.page_text_and_html()

    def page_images(self) -> List[str]:
        return self._impl.page_images()

    def eval_json(self, expression: str) -> Any:
        return self._impl.eval_json(expression)


def _open_browser_impl(log: Callable[[str], None]) -> Any:
    try:
        impl = _PlaywrightImpl()
        log("Playwright engine ready")
        return impl
    except Exception as pw_err:  # noqa: BLE001
        logger.warning("Playwright unavailable (%s); Selenium fallback", pw_err)
        log(f"Playwright failed ({pw_err}); opening Selenium fallback")
        return _SeleniumImpl()


class _PlaywrightImpl:
    engine = "playwright"

    def __init__(self) -> None:
        from playwright.sync_api import sync_playwright  # type: ignore

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._context = self._browser.new_context(
            user_agent=_ua(),
            java_script_enabled=True,
            locale="vi-VN",
            viewport={"width": 1400, "height": 900},
        )
        self._page = self._context.new_page()

    def close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._pw.stop()

    def goto(self, url: str, *, timeout_ms: int) -> str:
        self._page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        return self._page.url

    def wait_ms(self, ms: int) -> None:
        self._page.wait_for_timeout(ms)

    def wait_for_promo_links(self, *, timeout_ms: int) -> int:
        selectors = [
            'a[href*="/visa-offers-and-perks/"]',
            "article a[href]",
            '[role="main"] a[href*="visa-offers"]',
            "main a[href]",
        ]
        deadline = time.time() + timeout_ms / 1000.0
        last = 0
        while time.time() < deadline:
            for sel in selectors:
                try:
                    self._page.wait_for_selector(sel, timeout=2500)
                except Exception:
                    continue
            last = self.count_promo_links()
            if last > 0:
                return last
            self._page.wait_for_timeout(500)
        return last

    def scroll_to_bottom(self) -> None:
        self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    def click_load_more(self) -> int:
        clicked = 0
        # Role/text based — avoid fragile CSS classes
        try:
            buttons = self._page.get_by_role("button")
            n = buttons.count()
            for i in range(min(n, 40)):
                btn = buttons.nth(i)
                try:
                    label = (btn.inner_text(timeout=500) or "").strip()
                except Exception:
                    continue
                if label and LOAD_MORE_RE.search(label) and btn.is_visible():
                    btn.click(timeout=2000)
                    clicked += 1
                    self._page.wait_for_timeout(900)
        except Exception:
            pass
        try:
            links = self._page.get_by_role("link")
            n = links.count()
            for i in range(min(n, 40)):
                el = links.nth(i)
                try:
                    label = (el.inner_text(timeout=400) or "").strip()
                except Exception:
                    continue
                if label and LOAD_MORE_RE.search(label) and el.is_visible():
                    el.click(timeout=2000)
                    clicked += 1
                    self._page.wait_for_timeout(900)
        except Exception:
            pass
        # Generic elements with accessible name / text
        try:
            clicked += self._page.evaluate(
                """() => {
                  const re = /load\\s*more|show\\s*more|see\\s*more|xem\\s*thêm|tải\\s*thêm|hiển\\s*thị\\s*thêm/i;
                  let n = 0;
                  for (const el of document.querySelectorAll('button, a, [role="button"]')) {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (t && re.test(t) && el.offsetParent !== null) {
                      el.click();
                      n++;
                    }
                  }
                  return n;
                }"""
            )
        except Exception:
            pass
        return clicked

    def count_promo_links(self) -> int:
        return len(self.collect_promo_links())

    def collect_promo_links(self) -> List[Dict[str, str]]:
        return self._page.evaluate(
            """() => {
              const re = /\\/visa-offers-and-perks\\/[^/]+\\/\\d+/i;
              const seen = new Set();
              const out = [];
              for (const a of document.querySelectorAll('a[href*="/visa-offers-and-perks/"]')) {
                const href = a.href || a.getAttribute('href') || '';
                if (!re.test(href)) continue;
                const key = href.split('?')[0].split('#')[0];
                if (seen.has(key)) continue;
                seen.add(key);
                const title = (a.getAttribute('aria-label') || a.innerText || a.textContent || '').trim().replace(/\\s+/g, ' ');
                out.push({ href: key, title: title.slice(0, 200) });
              }
              // Also cards wrapped in article / listitem
              for (const card of document.querySelectorAll('article, li, [role="listitem"], [role="article"]')) {
                const a = card.querySelector('a[href*="/visa-offers-and-perks/"]');
                if (!a) continue;
                const href = (a.href || '').split('?')[0].split('#')[0];
                if (!re.test(href) || seen.has(href)) continue;
                seen.add(href);
                const title = (card.innerText || a.innerText || '').trim().split('\\n')[0].slice(0, 200);
                out.push({ href, title });
              }
              return out;
            }"""
        )

    def page_text_and_html(self) -> Tuple[str, str]:
        text = self._page.evaluate(
            """() => {
              const main = document.querySelector('main, [role="main"], app-root, article') || document.body;
              return (main.innerText || '').trim();
            }"""
        )
        html = self._page.content()
        return text or "", html or ""

    def page_images(self) -> List[str]:
        return self._page.evaluate(
            """() => [...document.querySelectorAll('img[src]')]
              .map(i => i.src)
              .filter(s => s && /^https?:/i.test(s) && !/logo\\.png|favicon|sprite/i.test(s))
              .slice(0, 20)"""
        )

    def eval_json(self, expression: str) -> Any:
        return self._page.evaluate(expression)


class _SeleniumImpl:
    engine = "selenium"

    def __init__(self) -> None:
        from selenium import webdriver  # type: ignore
        from selenium.webdriver.chrome.options import Options  # type: ignore

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1400,900")
        opts.add_argument(f"--user-agent={_ua()}")
        self._driver = webdriver.Chrome(options=opts)

    def close(self) -> None:
        self._driver.quit()

    def goto(self, url: str, *, timeout_ms: int) -> str:
        self._driver.set_page_load_timeout(max(10, timeout_ms // 1000))
        self._driver.get(url)
        # Approximate networkidle: short settle
        time.sleep(2.5)
        return self._driver.current_url

    def wait_ms(self, ms: int) -> None:
        time.sleep(ms / 1000.0)

    def wait_for_promo_links(self, *, timeout_ms: int) -> int:
        from selenium.webdriver.common.by import By  # type: ignore
        from selenium.webdriver.support import expected_conditions as EC  # type: ignore
        from selenium.webdriver.support.ui import WebDriverWait  # type: ignore

        try:
            WebDriverWait(self._driver, max(5, timeout_ms // 1000)).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/visa-offers-and-perks/"]'))
            )
        except Exception:
            pass
        return self.count_promo_links()

    def scroll_to_bottom(self) -> None:
        self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")

    def click_load_more(self) -> int:
        from selenium.webdriver.common.by import By  # type: ignore

        clicked = 0
        for el in self._driver.find_elements(By.CSS_SELECTOR, 'button, a, [role="button"]'):
            try:
                label = (el.text or "").strip()
                if label and LOAD_MORE_RE.search(label) and el.is_displayed():
                    el.click()
                    clicked += 1
                    time.sleep(0.9)
            except Exception:
                continue
        return clicked

    def count_promo_links(self) -> int:
        return len(self.collect_promo_links())

    def collect_promo_links(self) -> List[Dict[str, str]]:
        return self._driver.execute_script(
            """
            const re = /\\/visa-offers-and-perks\\/[^/]+\\/\\d+/i;
            const seen = new Set();
            const out = [];
            for (const a of document.querySelectorAll('a[href*="/visa-offers-and-perks/"]')) {
              const href = (a.href || '').split('?')[0].split('#')[0];
              if (!re.test(href) || seen.has(href)) continue;
              seen.add(href);
              out.push({ href, title: (a.innerText || '').trim().slice(0, 200) });
            }
            return out;
            """
        )

    def page_text_and_html(self) -> Tuple[str, str]:
        text = self._driver.execute_script(
            """
            const main = document.querySelector('main, [role="main"], app-root, article') || document.body;
            return (main.innerText || '').trim();
            """
        )
        return text or "", self._driver.page_source or ""

    def page_images(self) -> List[str]:
        return self._driver.execute_script(
            """
            return [...document.querySelectorAll('img[src]')]
              .map(i => i.src)
              .filter(s => s && /^https?:/i.test(s))
              .slice(0, 20);
            """
        )

    def eval_json(self, expression: str) -> Any:
        return self._driver.execute_script(f"return ({expression})")
