"""
KURT v3.0 — Web Browsing Engine
Kurt pwedeng mag-browse ng web — search, read pages, fill forms, click buttons.
100% libre, walang API key. Gumagamit ng Playwright (local browser automation).

Capabilities:
- Web search (DuckDuckGo — walang API key)
- Open any URL
- Read page content
- Click elements
- Fill forms / type text
- Take page screenshots
- Extract structured data
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────

@dataclass
class BrowseResult:
    success: bool
    url: str = ""
    title: str = ""
    content: str = ""
    links: list[dict] = field(default_factory=list)
    screenshot_b64: str = ""
    error: str = ""
    status_code: int = 0
    content_type: str = ""
    truncated: bool = False
    fetched_at: str = ""
    controls: list[dict] = field(default_factory=list)
    backend: str = ""


@dataclass
class SearchResult:
    success: bool
    query: str = ""
    results: list[dict] = field(default_factory=list)
    error: str = ""

    def top(self, n: int = 3) -> list[dict]:
        return self.results[:n]

    def summary(self) -> str:
        if not self.results:
            return "Walang nahanap."
        lines = []
        for i, r in enumerate(self.results[:8], 1):
            lines.append(f"{i}. {r.get('title', 'No title')}")
            lines.append(f"   {r.get('url', '')}")
            if r.get("snippet"):
                lines.append(f"   {r['snippet'][:350]}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# DuckDuckGo & Google News RSS Search — libre, walang API key
# ─────────────────────────────────────────────────────────────

def _clean_search_query(query: str) -> str:
    """Strip common conversational Tagalog/Taglish/English request wrappers for cleaner search queries."""
    q = (query or "").strip()
    q = re.sub(
        r"^(?:(?:hey\s+)?kurt[,!:\s]+)?(?:pwede\s+(?:mo\s+)?(?:bang\s+)?|paki\s+|please\s+)?"
        r"(?:tingnan\s+mo\s+(?:nga\s+)?(?:kung\s+)?|hanapin\s+mo\s+(?:nga\s+)?(?:kung\s+)?|"
        r"i-?search\s+mo\s+(?:nga\s+)?(?:kung\s+)?|maghanap\s+(?:ka\s+)?(?:ng\s+)?)?",
        "",
        q,
        flags=re.IGNORECASE,
    ).strip()
    return q or (query or "").strip()


def _brave_search(query: str, max_results: int) -> list[dict]:
    """Brave Search API — needs BRAVE_API_KEY. 2,000 free queries/month."""
    import os, requests
    key = os.getenv("BRAVE_API_KEY", "")
    if not key:
        raise RuntimeError("BRAVE_API_KEY not set")
    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"Accept": "application/json", "Accept-Encoding": "gzip", "X-Subscription-Token": key},
        params={"q": query, "count": max_results},
        timeout=10,
    )
    resp.raise_for_status()
    rows = resp.json().get("web", {}).get("results", [])
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("description", "")}
        for r in rows[:max_results]
    ]


def _serper_search(query: str, max_results: int) -> list[dict]:
    """Serper (Google results as JSON) — needs SERPER_API_KEY. 2,500 free searches on signup."""
    import os, requests
    key = os.getenv("SERPER_API_KEY", "")
    if not key:
        raise RuntimeError("SERPER_API_KEY not set")
    resp = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": key, "Content-Type": "application/json"},
        json={"q": query, "num": max_results},
        timeout=10,
    )
    resp.raise_for_status()
    rows = resp.json().get("organic", [])
    return [
        {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")}
        for r in rows[:max_results]
    ]


def _google_news_rss(query: str, max_results: int = 5) -> list[dict]:
    """Fetch live dated headlines from Google News RSS (free, no API key)."""
    import html as _html
    import xml.etree.ElementTree as ET

    params = urllib.parse.urlencode({"q": query, "hl": "en-PH", "gl": "PH", "ceid": "PH:en"})
    url = f"https://news.google.com/rss/search?{params}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        xml_bytes = resp.read()

    root = ET.fromstring(xml_bytes)
    results = []
    for item in root.findall(".//item")[:max_results]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        desc_raw = item.findtext("description") or ""
        desc_clean = _html.unescape(re.sub(r"<[^>]+>", " ", desc_raw))
        desc_clean = re.sub(r"\s+", " ", desc_clean).strip()
        prefix = f"[{pub_date}]" + (f" ({source})" if source else "")
        snippet = f"{prefix} {desc_clean or title}".strip()
        if title:
            results.append({"title": title, "url": link, "snippet": snippet})
    return results


def search_web(query: str, max_results: int = 5) -> SearchResult:
    """
    Search the live web and news. Uses configured API keys (Brave/Serper) if present,
    then combines DuckDuckGo HTML search and Google News RSS so both general web
    knowledge and up-to-the-minute dated news are returned without needing API keys.
    """
    if not isinstance(query, str) or not query.strip():
        return SearchResult(success=False, query=str(query or ""), error="Empty search query.")
    max_results = max(1, min(int(max_results or 5), 10))
    clean_q = _clean_search_query(query)
    errors = []

    # 1. Brave Search (needs BRAVE_API_KEY)
    try:
        results = _brave_search(clean_q, max_results)
        if results:
            return SearchResult(success=True, query=query, results=results)
    except Exception as e:
        errors.append(f"brave: {e}")

    # 2. Serper (needs SERPER_API_KEY)
    try:
        results = _serper_search(clean_q, max_results)
        if results:
            return SearchResult(success=True, query=query, results=results)
    except Exception as e:
        errors.append(f"serper: {e}")

    # 3. Free live search: DuckDuckGo HTML POST + Google News RSS
    ddg_results = []
    news_results = []
    try:
        ddg_results = _ddg_scrape(clean_q, max_results)
    except Exception as e:
        errors.append(f"ddg_scrape: {e}")

    try:
        news_results = _google_news_rss(clean_q, max(3, max_results // 2 + 1))
    except Exception as e:
        errors.append(f"google_news: {e}")

    is_news_query = bool(
        re.search(
            r"\b(news|balita|latest|today|ngayon|recent|current|update|updates|nangyari|happened|2024|2025|2026|2027|kahapon|kailan)\b",
            clean_q,
            re.IGNORECASE,
        )
    )

    combined = []
    seen_urls = set()
    primary = (news_results + ddg_results) if is_news_query else (ddg_results + news_results)
    for item in primary:
        u = item.get("url", "")
        key = u or item.get("title", "")
        if key and key not in seen_urls:
            seen_urls.add(key)
            combined.append(item)
        if len(combined) >= max_results:
            break

    if combined:
        return SearchResult(success=True, query=query, results=combined[:max_results])

    # 4. Last resort: ddgs library
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw = list(ddgs.text(clean_q, max_results=max_results))
        results = [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in raw
        ]
        if results:
            return SearchResult(success=True, query=query, results=results)
        errors.append("ddgs: no results")
    except ImportError:
        pass
    except Exception as e:
        errors.append(f"ddgs: {e}")

    return SearchResult(success=False, query=query, error="; ".join(errors) or "No results found.")


def _ddg_scrape(query: str, max_results: int = 5) -> list[dict]:
    """Scrape DuckDuckGo HTML search results via POST (handles bold tags in snippets)."""
    import html as _html

    url = "https://html.duckduckgo.com/html/"
    data = urllib.parse.urlencode({"q": query}).encode("utf-8")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw_html = resp.read().decode("utf-8", errors="ignore")

    results = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw_html, "html.parser")
        for block in soup.select(".result"):
            a = block.select_one(".result__a")
            if not a:
                continue
            href = a.get("href", "")
            if "duckduckgo.com/y.js" in href or "ad_domain" in href:
                continue
            if href.startswith("//duckduckgo.com/l/?uddg="):
                href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
            s = block.select_one(".result__snippet")
            results.append({
                "title": a.get_text(" ", strip=True),
                "url": href,
                "snippet": s.get_text(" ", strip=True) if s else "",
            })
            if len(results) >= max_results:
                break
        if results:
            return results
    except ImportError:
        pass

    pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>'

    links = re.findall(pattern, raw_html, re.DOTALL)
    snippets = re.findall(snippet_pattern, raw_html, re.DOTALL)

    for i, (href, title_html) in enumerate(links):
        if "duckduckgo.com/y.js" in href or "ad_domain" in href:
            continue
        if href.startswith("//duckduckgo.com/l/?uddg="):
            href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
        title = _html.unescape(re.sub(r"<[^>]+>", " ", title_html))
        title = re.sub(r"\s+", " ", title).strip()
        snip_raw = snippets[i] if i < len(snippets) else ""
        snip = _html.unescape(re.sub(r"<[^>]+>", " ", snip_raw))
        snip = re.sub(r"\s+", " ", snip).strip()
        results.append({
            "title": title,
            "url": href,
            "snippet": snip,
        })
        if len(results) >= max_results:
            break
    return results


# ─────────────────────────────────────────────────────────────
# Page Reader — simple version without Playwright
# ─────────────────────────────────────────────────────────────

MAX_FETCH_BYTES = 2 * 1024 * 1024


def read_page(url: str, extract_text: bool = True) -> BrowseResult:
    """Bounded HTTP(S) fetch with final URL, text extraction and usable links."""
    import httpx
    from datetime import datetime, timezone
    from kurt.utils.security import redact
    status, content_type = 0, ""
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Use an HTTP(S) URL without embedded credentials.")
        with httpx.Client(timeout=15, follow_redirects=True, max_redirects=5) as client:
            with client.stream("GET", url, headers={"User-Agent": "Kurt/3 WebReader"}) as response:
                status = response.status_code
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if content_type and not (content_type.startswith("text/") or content_type in {
                    "application/json", "application/ld+json", "application/xml", "application/xhtml+xml"}):
                    raise ValueError("This URL returns a binary document; use its dedicated file reader.")
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_FETCH_BYTES:
                        raise ValueError("Page exceeds the 2 MiB fetch limit; request a smaller resource.")
                    chunks.append(chunk)
                html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
                final_url = str(response.url)
        title, content, links = "", html, []
        if extract_text and (content_type in ("text/html", "application/xhtml+xml") or (not content_type and "<" in html)):
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                title = soup.title.get_text(" ", strip=True) if soup.title else ""
                base = soup.find("base", href=True)
                base_url = urllib.parse.urljoin(final_url, base["href"]) if base else final_url
                for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
                    tag.decompose()
                for anchor in soup.find_all("a", href=True):
                    href = urllib.parse.urljoin(base_url, anchor["href"])
                    if urllib.parse.urlsplit(href).scheme in ("http", "https"):
                        links.append({"text": anchor.get_text(" ", strip=True)[:100], "url": href})
                    if len(links) >= 30:
                        break
                content = soup.get_text(separator="\n", strip=True)
            except ImportError:
                content = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
                content = re.sub(r"<[^>]+>", " ", content)
                import html as html_module
                content = html_module.unescape(content)
        if extract_text:
            content = "\n".join(line.strip() for line in content.splitlines() if line.strip())
        return BrowseResult(success=True, url=final_url, title=title, content=content[:8000], links=links,
                            status_code=status, content_type=content_type, truncated=len(content) > 8000,
                            fetched_at=datetime.now(timezone.utc).isoformat())
    except Exception as exc:
        return BrowseResult(success=False, url=url, error=redact(str(exc)), status_code=status, content_type=content_type)


# ─────────────────────────────────────────────────────────────
# Playwright Browser — full automation (optional, needs install)
# ─────────────────────────────────────────────────────────────

class KurtBrowser:
    """
    Full browser automation using Playwright.
    Kurt can click buttons, fill forms, navigate like a human.
    Install: pip install playwright && playwright install chromium
    """

    def __init__(self, headless: bool = True, slow_mo: int = 50):
        self.headless = headless
        self.slow_mo = slow_mo
        self._browser = None
        self._page = None
        self._context = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    def start(self):
        """Launch browser"""
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().__enter__()
            import os
            from pathlib import Path
            channel = os.getenv("KURT_BROWSER_CHANNEL", "").strip()
            if channel and channel not in ("chromium", "chrome", "msedge"):
                raise ValueError("KURT_BROWSER_CHANNEL must be chromium, chrome or msedge.")
            if not channel and not Path(self._pw.chromium.executable_path).exists():
                import platform
                if platform.system() == "Darwin":
                    from kurt.core.app_launcher import application_paths
                    apps = application_paths()
                    channel = "chrome" if "google chrome" in apps else ("msedge" if "microsoft edge" in apps else "")
                else:
                    import shutil
                    channel = "chrome" if any(shutil.which(c) for c in ("google-chrome", "chrome")) else ("msedge" if shutil.which("msedge") else "")
            self._browser = self._pw.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                **({"channel": channel} if channel else {}),
            )
            self.backend = channel or "bundled-chromium"
            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            self._page = self._context.new_page()
            logger.info("Browser started")
            return True
        except ImportError:
            raise ImportError(
                "Playwright not installed.\n"
                "Run: pip install playwright && playwright install chromium"
            )
        except Exception:
            self.close()
            raise

    def close(self):
        """Close browser"""
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if hasattr(self, "_pw"):
                self._pw.__exit__(None, None, None)
        except Exception:
            pass

    def go(self, url: str, wait_for: str = "domcontentloaded") -> BrowseResult:
        """Navigate to URL"""
        try:
            self._page.goto(url, wait_until=wait_for, timeout=30000)
            return self.read()
        except Exception as e:
            return BrowseResult(success=False, url=url, error=str(e))

    def read(self) -> BrowseResult:
        """Read current page content"""
        try:
            title = self._page.title()
            # Get text content
            content = self._page.evaluate("() => document.body.innerText")
            content = content or ""
            controls = self._page.locator("input, textarea, select, button, [role=button]").evaluate_all("""els => els.filter(e => e.getClientRects().length).slice(0, 40).map(e => ({tag:e.tagName.toLowerCase(), id:e.id, name:e.name || '', type:e.type || '', label:e.getAttribute('aria-label') || e.labels?.[0]?.innerText || '', placeholder:e.getAttribute('placeholder') || '', value:e.type === 'password' ? null : (e.value ?? null), text:(e.innerText || '').slice(0,100)}))""")
            url = self._page.url
            return BrowseResult(success=True, url=url, title=title, content=content[:8000],
                                links=self.get_links(), controls=controls, truncated=len(content) > 8000,
                                backend=getattr(self, 'backend', ''))
        except Exception as e:
            return BrowseResult(success=False, error=str(e))

    def click(self, selector: str = None, text: str = None, x: int = None, y: int = None) -> bool:
        """Click element by CSS selector, visible text, or coordinates"""
        try:
            if selector:
                self._page.locator(selector).click(timeout=5000)
            elif text:
                self._page.get_by_text(text, exact=True).click(timeout=5000)
            elif x is not None and y is not None:
                self._page.mouse.click(x, y)
            else:
                return False
            return True
        except Exception as e:
            logger.warning(f"Click failed: {e}")
            return False

    def type(self, selector: str, text: str, clear_first: bool = True) -> bool:
        """Type text into input field"""
        try:
            if clear_first:
                self._page.locator(selector).fill(text, timeout=5000)
            else:
                self._page.locator(selector).press_sequentially(text, timeout=5000)
            return True
        except Exception as e:
            logger.warning(f"Type failed: {e}")
            return False

    def screenshot_b64(self) -> str:
        """Take screenshot of current page, return base64"""
        import base64
        try:
            data = self._page.screenshot(full_page=False)
            return base64.b64encode(data).decode()
        except Exception:
            return ""

    def wait_for_text(self, text: str, timeout: int = 10000) -> bool:
        """Wait until text appears on page"""
        try:
            self._page.wait_for_selector(f"text={text}", timeout=timeout)
            return True
        except Exception:
            return False

    def get_links(self) -> list[dict]:
        """Get all links on current page"""
        try:
            links = self._page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]'))
                    .slice(0, 30)
                    .map(a => ({text: a.innerText.trim().slice(0, 60), url: a.href}))
                    .filter(l => l.url.startsWith('http'))
            """)
            return links
        except Exception:
            return []

    def search(self, query: str, engine: str = "google") -> BrowseResult:
        """Search using browser"""
        engines = {
            "google": f"https://www.google.com/search?q={urllib.parse.quote(query)}",
            "duckduckgo": f"https://duckduckgo.com/?q={urllib.parse.quote(query)}",
            "bing": f"https://www.bing.com/search?q={urllib.parse.quote(query)}",
            "youtube": f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}",
        }
        url = engines.get(engine, engines["google"])
        result = self.go(url)
        if result.success:
            return self.read()
        return result

    def new_tab(self) -> None:
        """Open a new tab"""
        self._page = self._context.new_page()

    def execute_js(self, script: str):
        """Run JavaScript on current page"""
        try:
            return self._page.evaluate(script)
        except Exception as e:
            logger.warning(f"JS execution failed: {e}")
            return None


# ─────────────────────────────────────────────────────────────
# High-level convenience functions
# ─────────────────────────────────────────────────────────────

def quick_search_and_read(query: str) -> str:
    """
    Search web and read top result.
    Returns combined summary string.
    """
    search = search_web(query, max_results=3)
    if not search.success or not search.results:
        return f"Hindi nahanap ang '{query}'"

    output = [f"Search results para sa: {query}\n"]
    for i, r in enumerate(search.results[:3], 1):
        output.append(f"{i}. {r['title']}")
        output.append(f"   {r['url']}")
        if r.get("snippet"):
            output.append(f"   {r['snippet'][:200]}")
        output.append("")

    # Read top result
    top = search.results[0]
    page = read_page(top["url"])
    if page.success and page.content:
        output.append(f"\n--- Nilalaman ng unang result ---")
        output.append(page.content[:2000])

    return "\n".join(output)


def install_dependencies() -> dict[str, str]:
    """Install web browsing dependencies"""
    import subprocess
    packages = ["requests", "beautifulsoup4", "duckduckgo-search", "playwright"]
    results = {}
    for pkg in packages:
        r = subprocess.run(
            ["pip", "install", pkg, "--break-system-packages", "-q"],
            capture_output=True, text=True
        )
        results[pkg] = "ok" if r.returncode == 0 else "failed"
    return results


def check_dependencies() -> dict[str, bool]:
    """Check web browsing dependencies"""
    deps = {}
    for pkg in ["requests", "bs4", "duckduckgo_search", "playwright"]:
        try:
            __import__(pkg)
            deps[pkg] = True
        except ImportError:
            deps[pkg] = False
    deps["can_search"] = True  # urllib always works
    deps["can_read_pages"] = True  # urllib always works
    deps["can_automate"] = deps.get("playwright", False)
    return deps


class BrowserSession:
    """Keep all Playwright creation/actions/cleanup on one dedicated thread."""
    def __init__(self, **options):
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="Kurt-Browser")
        self._options = options
        self._browser = None
        self._closed = False

    def _call(self, name, args, kwargs):
        if self._browser is None:
            self._browser = KurtBrowser(**self._options)
        return getattr(self._browser, name)(*args, **kwargs)

    def __getattr__(self, name):
        if name not in {"start", "go", "read", "click", "type", "screenshot_b64", "get_links", "search", "wait_for_text", "new_tab", "execute_js"}:
            raise AttributeError(name)
        def invoke(*args, **kwargs):
            if self._closed:
                raise RuntimeError("Browser session is closed.")
            return self._executor.submit(self._call, name, args, kwargs).result()
        return invoke

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._executor.submit(self._call, "close", (), {}).result()
        finally:
            self._executor.shutdown(wait=True)
