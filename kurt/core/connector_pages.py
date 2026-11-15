"""Published setup links shared by the connector picker and guided connect.

Unknown services keep their publisher's links; never guess an API-key URL
from an app name. Browsing this metadata does not start a server.
"""

import webbrowser
from urllib.parse import quote, urlsplit


PRESET_PAGES = {
    "github": {"API keys": "https://github.com/settings/tokens", "GitHub / source": "https://github.com/github/github-mcp-server"},
    "brave-search": {"API keys": "https://api.search.brave.com/app/keys", "GitHub / source": "https://github.com/brave/brave-search-mcp-server"},
    "filesystem": {"GitHub / source": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem"},
    "postgres": {"GitHub / source": "https://github.com/modelcontextprotocol/servers-archived/tree/main/src/postgres"},
    "sqlite": {"Package / setup instructions": "https://www.npmjs.com/package/mcp-sqlite-server"},
    "puppeteer": {"GitHub / source": "https://github.com/microsoft/playwright-mcp"},
}

PLATFORM_PAGES = {
    "composio": {
        "Composio API key / dashboard": "https://dashboard.composio.dev/",
        "Authentication setup": "https://docs.composio.dev/docs/tools-direct/authenticating-tools",
        "GitHub / source": "https://github.com/ComposioHQ/composio",
    },
    "zapier": {
        "Create MCP server / connect accounts": "https://mcp.zapier.com/",
        "MCP setup instructions": "https://docs.zapier.com/mcp/quickstart",
    },
    "n8n": {
        "MCP access / token instructions": "https://docs.n8n.io/connect/connect-to-n8n-mcp-server/",
        "API key instructions": "https://docs.n8n.io/api/authentication/",
        "GitHub / source": "https://github.com/n8n-io/n8n",
    },
}


def public_page(url):
    """Only web pages, without embedded credentials or control characters."""
    if not isinstance(url, str) or any(ord(c) < 32 for c in url):
        return ""
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
            return ""
    except ValueError:
        return ""
    return url


def entry_pages(entry):
    pages = {}
    for label, key in (("Website / setup instructions", "website"), ("GitHub / source", "repository")):
        url = public_page(entry.get(key))
        if url:
            pages[label] = url
    # Some publishers only provide a package recipe. The package registry
    # page is a real setup source, without guessing a vendor dashboard.
    if not pages:
        for package in entry.get("setup", {}).get("packages", []):
            identifier = package.get("identifier")
            kind = package.get("registryType")
            if identifier and kind in ("npm", "pypi"):
                base = "https://www.npmjs.com/package/" if kind == "npm" else "https://pypi.org/project/"
                pages[f"Package / setup instructions ({identifier})"] = base + quote(identifier, safe="@/")
    return pages


def connector_pages(provider, ref, entry=None):
    if provider == "mcp":
        return dict(PRESET_PAGES[ref]) if ref in PRESET_PAGES else entry_pages(entry or {})
    pages = dict(PLATFORM_PAGES[provider])
    slug = quote(ref, safe="")
    if provider == "composio":
        pages = {"App authentication / API instructions": f"https://composio.dev/toolkits/{slug}", **pages}
    elif provider == "zapier":
        pages = {"App integration / account setup": f"https://zapier.com/apps/{slug}/integrations", **pages}
    elif provider == "n8n":
        pages = {"App integration / credential instructions": f"https://n8n.io/integrations/{slug}/", **pages}
    return pages


def open_page(url):
    url = public_page(url)
    if not url:
        return "No valid website was published for this connector."
    try:
        if webbrowser.open(url):
            return f"Opened {url} — return here to continue connecting."
    except Exception:
        pass
    return f"Browser unavailable. Open this link manually: {url}"
