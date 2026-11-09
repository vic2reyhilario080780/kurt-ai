# MCP catalog and paste-to-connect

Kurt ships an offline, searchable snapshot of the public
[official MCP registry](https://registry.modelcontextprotocol.io/).
The November 9, 2026 snapshot contains **58,869 distinct active server names**,
of which **55,752 have at least one supported connection recipe**.
These are server listings, not a count of unique apps. The publisher provides
the connection details; inclusion does not mean Kurt tested the endpoint.

## Find an app and copy its config

```sh
kurt mcp catalog
kurt mcp search github
kurt mcp info <server-id>
kurt mcp config <server-id> --output app-mcp.json
```

Some entries have several recipes. `--variant 1` exports the second recipe
(numbering starts at zero). `info` shows all recipes and the original setup
fields, including package/environment/header requirements.

Open `app-mcp.json` and fill any placeholders with the app's URL, API key,
access token or other required values. `${ENV_NAME}` references can instead
be resolved from Kurt's environment at import time.

```sh
kurt mcp connect app-mcp.json
```

`connect` saves the selected configuration, initializes a real MCP session and
lists its tools. It reports failed authentication or connection attempts and
exits with a nonzero status on failure. An MCP with no tools can still connect
successfully. Failed connections remain saved for editing/retrying.

## Paste an existing app config

In `kurt chat`, paste one JSON object on a single line after `/mcp connect`:

```text
/mcp connect {"mcpServers":{"my-app":{"url":"https://example.com/mcp","headers":{"Authorization":"Bearer YOUR_TOKEN"}}}}
```

For a public endpoint without credentials:

```text
/mcp connect https://example.com/mcp
```

These are syntax examples; `example.com` is not an actual MCP endpoint.
Kurt accepts Claude-style `mcpServers`, VS Code-style `servers`, a plain server
map, or a single config with `--name`. Both URL and stdio command/args configs
are supported. Legacy SSE configs must explicitly use `"type":"sse"`.

The terminal supports files, quoted JSON, URLs or standard input:

```sh
kurt mcp connect copied-config.json
kurt mcp connect -
kurt mcp import copied-config.json
kurt mcp test my-app
```

For `connect -`, paste JSON into standard input and finish with Ctrl-D.
`import` only saves; `connect` additionally contacts the server or starts the
configured local process. To update an existing saved name use `--replace`.
Incomplete placeholders and name collisions are rejected before saving.
Secrets are saved in an atomically replaced connection file with mode 0600.

## Use it from chat

```text
/mcp catalog
/mcp search notion
/mcp config <server-id>
/mcp connect <copied JSON or URL>
/mcp list
/mcp tools
/mcp call my-app/tool-name {"argument":"value"}
```

Only explicitly imported connections enter `~/.kurt/mcp_connections.json`.
Catalog servers are not automatically enabled or started. Once imported,
connections use Kurt's existing MCP tool discovery and agent loop.

## Refresh and compatibility

```sh
kurt mcp sync
```

Refreshes `~/.kurt/mcp_public_catalog.json` without modifying connections.
The bundled catalog is `kurt/data/mcp_catalog.json.gz`. Both include source,
snapshot timestamp, deduplicated IDs, connection recipes and original setup
details. A failed refresh preserves the existing file.

Connections use the official MCP Python SDK for initialization, protocol
negotiation, HTTP session IDs, SSE event streams, tool pagination and process
cleanup. Runtime requirements are installed through `requirements.txt` or
`pip install -e .`.

Remote HTTP and SSE and local stdio are supported. Generated package recipes
cover npm (`npx`, requires Node.js) and PyPI (`uvx`, requires uv). Other package
types remain discoverable with original setup details, but require manual
configuration. OAuth browser sign-in is not implemented: supply a valid API
key/access token when the app allows it. Private endpoints, paid subscriptions,
app permissions and changing or unavailable servers can require additional
setup. The catalog does not promise 10,000 authenticated, live app connections.
