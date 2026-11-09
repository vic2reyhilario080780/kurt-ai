"""Public MCP discovery and explicit, non-executing configuration import.

Registry entries describe servers, not necessarily unique apps or working services.
Only an explicit connection test starts a package or contacts a server.
"""

from kurt.utils.security import require_secure_endpoint

import json
import gzip
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"
BUNDLED_CATALOG = Path(__file__).parents[1] / "data" / "mcp_catalog.json.gz"
USER_CATALOG = Path.home() / ".kurt" / "mcp_public_catalog.json"


def catalog_path():
    return USER_CATALOG if USER_CATALOG.exists() else BUNDLED_CATALOG


def load_catalog(path=None):
    p = Path(path) if path else catalog_path()
    if not p.exists():
        return {"entries": [], "source": REGISTRY_URL}
    if p.suffix == ".gz":
        with gzip.open(p, "rt") as stream:
            return json.load(stream)
    return json.loads(p.read_text())


def search_catalog(query="", limit=20, path=None):
    words = query.casefold().split()
    entries = load_catalog(path)["entries"]
    matches = [e for e in entries if all(
        word in (e["id"] + " " + e.get("title", "") + " " + e.get("description", "")).casefold()
        for word in words
    )]
    def score(entry):
        title = entry.get("title", "").casefold()
        short_id = entry["id"].split("/", 1)[-1].casefold()
        return (-(100 if title == query.casefold() or short_id == query.casefold() else 0)
                - sum(10 for w in words if w in title or w in short_id), entry["id"])
    return sorted(matches, key=score)[:limit]


def _variable(item):
    return "${" + item["name"] + "}"


def registry_entry(row):
    """Keep source provenance and actual published connection recipes."""
    server = row.get("server", row)
    meta = row.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
    if meta.get("status", "active") != "active" or meta.get("isLatest") is False:
        return None
    name = server.get("name")
    if not name:
        return None
    recipes = []
    for remote in server.get("remotes", []):
        if remote.get("type") not in ("streamable-http", "sse") or not remote.get("url"):
            continue
        headers = {}
        for h in remote.get("headers", []):
            headers[h["name"]] = h.get("value") or _variable(h)
        recipes.append({"type": remote["type"], "url": remote["url"], "headers": headers})
    for package in server.get("packages", []):
        transport = package.get("transport", {}).get("type")
        kind = package.get("registryType")
        identifier = package.get("identifier")
        if transport != "stdio" or not identifier or kind not in ("npm", "pypi"):
            continue
        version = package.get("version")
        spec = identifier + (("@" if kind == "npm" else "==") + version if version else "")
        args = []
        # Runtime options belong before the package identifier.
        for arg in package.get("runtimeArguments", []):
            args.extend(_argument(arg))
        command = "npx" if kind == "npm" else "uvx"
        args = (["-y"] if kind == "npm" else []) + args + [spec]
        for arg in package.get("packageArguments", []):
            args.extend(_argument(arg))
        env = {v["name"]: v.get("value") or _variable(v)
               for v in package.get("environmentVariables", [])
               if v.get("isRequired", False) or v.get("value")}
        recipes.append({"command": command, "args": args, "env": env, "type": "stdio"})
    return {
        "id": name, "title": server.get("title", name),
        "description": server.get("description", ""), "version": server.get("version", ""),
        "website": server.get("websiteUrl", ""), "repository": server.get("repository", {}).get("url", ""),
        "source": REGISTRY_URL, "verification": "listed; connection not tested",
        "configs": recipes,
        # Preserve required fields/auth hints for recipes that need user setup.
        "setup": {k: server[k] for k in ("remotes", "packages") if k in server},
    }


def _argument(arg):
    value = arg.get("value")
    if value is None:
        if not arg.get("isRequired", False):
            return []
        value = "${" + (arg.get("valueHint") or arg.get("name") or "ARGUMENT").lstrip("-") + "}"
    result = [str(value)]
    if arg.get("type") == "named" and arg.get("name"):
        result.insert(0, arg["name"])
    return result


def sync_catalog(path=None, progress=None):
    """Page through the public registry, deduplicate by name, save atomically."""
    entries = {}
    cursor = None
    seen = set()
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        while True:
            params = {"limit": 100, "version": "latest"}
            if cursor:
                params["cursor"] = cursor
            for attempt in range(5):
                try:
                    response = client.get(REGISTRY_URL, params=params)
                    response.raise_for_status()
                    page = response.json()
                    break
                except (httpx.HTTPError, ValueError):
                    if attempt == 4:
                        raise
                    time.sleep(min(2 ** attempt, 8))
            for row in page.get("servers", []):
                entry = registry_entry(row)
                if entry:
                    entries[entry["id"]] = entry
            if progress:
                progress(len(entries))
            cursor = page.get("metadata", {}).get("nextCursor")
            if not cursor:
                break
            if cursor in seen:
                raise ValueError("Registry returned a repeated cursor; keeping the existing catalog.")
            seen.add(cursor)
    data = {"source": REGISTRY_URL, "fetched_at": datetime.now(timezone.utc).isoformat(),
            "count": len(entries), "entries": sorted(entries.values(), key=lambda e: e["id"])}
    target = Path(path) if path else USER_CATALOG
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    content = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if target.suffix == ".gz":
        with gzip.open(tmp, "wt") as stream:
            stream.write(content)
    else:
        tmp.write_text(content)
    tmp.replace(target)
    return data


def export_config(server_id, variant=0, path=None):
    entry = next((e for e in load_catalog(path)["entries"] if e["id"] == server_id), None)
    if entry is None:
        raise ValueError("Server not found. Use: kurt mcp search <name>")
    if variant < 0 or variant >= len(entry["configs"]):
        raise ValueError("No supported config at this variant. See the entry's setup instructions.")
    return {"mcpServers": {entry["id"]: entry["configs"][variant]}}


def _expand(value):
    if isinstance(value, str):
        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}",
                      lambda m: os.environ.get(m[1], m[0]), value)
    if isinstance(value, list):
        return [_expand(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    return value


def _has_placeholders(value):
    if isinstance(value, str):
        return bool(re.search(r"\$\{[^}]+\}|\{[A-Za-z_][A-Za-z0-9_.-]*\}|<[A-Za-z_][A-Za-z0-9_ -]*>", value))
    if isinstance(value, dict):
        return any(_has_placeholders(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_placeholders(v) for v in value)
    return False


def parse_config(raw, name=None):
    """Accept a URL, Claude mcpServers, VS Code servers, or a single config."""
    from kurt.core.mcp_client import MCPConnection

    if raw.strip().startswith(("https://", "http://")):
        if not name:
            name = urlparse(raw.strip()).hostname
        data = {name: {"url": raw.strip()}}
    else:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("MCP configuration must be a JSON object.")
        if "mcpServers" in data or "servers" in data:
            data = data.get("mcpServers", data.get("servers"))
        elif "url" in data or "command" in data:
            if not name:
                raise ValueError("A single config needs --name.")
            data = {name: data}
    if not isinstance(data, dict) or not data:
        raise ValueError("Configuration contains no servers.")
    connections = []
    for server_name, config in data.items():
        if not isinstance(server_name, str) or not server_name or not isinstance(config, dict):
            raise ValueError("Invalid server name or configuration.")
        if config.get("oauth") or config.get("auth"):
            raise ValueError(f"{server_name}: OAuth needs an access token; supply Authorization headers.")
        cfg = _expand(config)
        if _has_placeholders(cfg):
            raise ValueError(f"{server_name}: fill the config placeholders or set their environment variables first.")
        transport = cfg.get("transport", cfg.get("type")) or ("http" if cfg.get("url") else "stdio")
        transport = {"streamable-http": "http", "streamableHttp": "http"}.get(transport, transport)
        if transport not in ("http", "sse", "stdio"):
            raise ValueError(f"{server_name}: unsupported transport {transport}.")
        env, headers, args = cfg.get("env", {}), cfg.get("headers", {}), cfg.get("args", [])
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise ValueError(f"{server_name}: args must be a list of strings.")
        for label, values in (("env", env), ("headers", headers)):
            if not isinstance(values, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
                raise ValueError(f"{server_name}: {label} must map strings to strings.")
        if transport == "stdio":
            if not isinstance(cfg.get("command"), str) or not cfg["command"].strip():
                raise ValueError(f"{server_name}: missing command.")
        elif not isinstance(cfg.get("url"), str) or urlparse(cfg["url"]).scheme not in ("https", "http") or not urlparse(cfg["url"]).netloc:
            raise ValueError(f"{server_name}: invalid HTTP URL.")
        if transport in ("http", "sse"):
            require_secure_endpoint(cfg["url"])
        connections.append(MCPConnection(name=server_name, transport=transport,
            command=cfg.get("command"), args=args, env=env, url=cfg.get("url"), headers=headers,
            enabled=cfg.get("enabled", not cfg.get("disabled", False)), description=cfg.get("description", "")))
    return connections


def import_config(raw, name=None, replace=False):
    from kurt.core.mcp_client import load_registry, save_registry

    connections = parse_config(raw, name)
    registry = load_registry()
    collisions = [c.name for c in connections if c.name in registry]
    if collisions and not replace:
        raise ValueError("Already registered: " + ", ".join(collisions) + ". Use --replace to update.")
    registry.update({c.name: c for c in connections})
    save_registry(registry)
    return [c.name for c in connections]
