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
        for i, r in enumerate(self.results[:5], 1):
            lines.append(f"{i}. {r.get('title', 'No title')}")
            lines.append(f"   {r.get('url', '')}")
            if r.get("snippet"):
                lines.append(f"   {r['snippet'][:150]}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# DuckDuckGo Search — libre, walang API key
# ─────────────────────────────────────────────────────────────

def search_web(query: str, max_results: int = 5) -> SearchResult:
    """
    Search the web using DuckDuckGo.
    No API key needed. Libre forever.
    """
    try:
        # Try ddgs library first (best results) — duckduckgo_search was renamed to ddgs
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in raw
            ]
            return SearchResult(success=True, query=query, results=results)
        except ImportError:
            pass

        # Fallback: scrape DuckDuckGo HTML
        results = _ddg_scrape(query, max_results)
        return SearchResult(success=True, query=query, results=results)

    except Exception as e:
        return SearchResult(success=False, query=query, error=str(e))


def _ddg_scrape(query: str, max_results: int = 5) -> list[dict]:
    """Scrape DuckDuckGo search results"""
    encoded = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/91.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    results = []
    # Simple regex parse — good enough
    pattern = r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
    snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]+)<'

    links = re.findall(pattern, html)
    snippets = re.findall(snippet_pattern, html)

    for i, (href, title) in enumerate(links[:max_results]):
        # Clean DuckDuckGo redirect URLs
        if href.startswith("//duckduckgo.com/l/?uddg="):
            href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
        results.append({
            "title": title.strip(),
            "url": href,
            "snippet": snippets[i].strip() if i < len(snippets) else "",
        })
    return results


# ─────────────────────────────────────────────────────────────
# Page Reader — simple version without Playwright
# ─────────────────────────────────────────────────────────────

def read_page(url: str, extract_text: bool = True) -> BrowseResult:
    """
    Read a web page content.
    Uses requests + BeautifulSoup if available, else urllib.
    """
    try:
        # Try with requests + bs4 (best)
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            html = resp.text
            title = ""
            content = html

            if extract_text:
                soup = BeautifulSoup(html, "html.parser")
                title = soup.title.string if soup.title else ""
                # Remove scripts/styles
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                content = soup.get_text(separator="\n", strip=True)
                # Clean up blank lines
                content = "\n".join(l for l in content.splitlines() if l.strip())
                content = content[:8000]  # Limit

            # Extract links
            links = []
            if extract_text:
                for a in soup.find_all("a", href=True)[:20]:
                    href = a["href"]
                    if href.startswith("http"):
                        links.append({"text": a.get_text(strip=True)[:50], "url": href})

            return BrowseResult(
                success=True, url=url, title=title,
                content=content, links=links
            )
        except ImportError:
            pass

        # Fallback: urllib only
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Basic text extraction
        content = re.sub(r"<[^>]+>", " ", html)
        content = re.sub(r"\s+", " ", content).strip()[:5000]
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""

        return BrowseResult(success=True, url=url, title=title, content=content)

    except Exception as e:
        return BrowseResult(success=False, url=url, error=str(e))


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
            self._browser = self._pw.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo
            )
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
            return BrowseResult(success=True, url=url, title=self._page.title())
        except Exception as e:
            return BrowseResult(success=False, url=url, error=str(e))

    def read(self) -> BrowseResult:
        """Read current page content"""
        try:
            title = self._page.title()
            # Get text content
            content = self._page.evaluate("() => document.body.innerText")
            content = content[:8000] if content else ""
            url = self._page.url
            return BrowseResult(success=True, url=url, title=title, content=content)
        except Exception as e:
            return BrowseResult(success=False, error=str(e))

    def click(self, selector: str = None, text: str = None, x: int = None, y: int = None) -> bool:
        """Click element by CSS selector, visible text, or coordinates"""
        try:
            if selector:
                self._page.click(selector, timeout=5000)
            elif text:
                self._page.get_by_text(text).first.click(timeout=5000)
            elif x is not None and y is not None:
                self._page.mouse.click(x, y)
            return True
        except Exception as e:
            logger.warning(f"Click failed: {e}")
            return False

    def type(self, selector: str, text: str, clear_first: bool = True) -> bool:
        """Type text into input field"""
        try:
            if clear_first:
                self._page.fill(selector, text)
            else:
                self._page.type(selector, text)
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
