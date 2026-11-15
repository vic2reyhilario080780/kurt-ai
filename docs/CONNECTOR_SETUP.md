# Connector setup in Kurt

Open `kurt chat`, type `/`, choose **MCP Connectors**, then `/mcp`.
Composio, Zapier, and n8n are also reachable inside this MCP list.
Search for a connector and press Enter to see its setup menu.

- **Connect / authorize** starts guided setup in the terminal.
- **Open API keys / setup instructions** opens the published setup page.
- **Open website / GitHub / source** opens the relevant page without closing the picker.
- **Test saved connection** contacts that server and lists its available tools.
- **Connect option** selects a particular recipe when a server publishes several.

Return from the browser to the same menu to continue. Esc returns to the
previous list. Selecting a connection action submits the actual command,
rather than leaving a search filter in the terminal echo.

## MCP servers

Kurt keeps both the publisher website and repository, instead of choosing
only one. Presets have explicit setup links. If no publisher links exist
but package metadata does, Kurt offers the npm/PyPI package instructions.
Unknown API dashboard URLs are not inferred from service names.

Guided setup opens the available setup pages and asks for missing values.
It supports environment variables, embedded placeholders, arguments and URL
templates. Existing HTTP credentials bypass unnecessary OAuth prompts.
Secrets are hidden while being entered; Ctrl-C cancels credential entry
without saving. OAuth is used when supported by the existing OAuth client.
Servers requiring other OAuth client registration methods can still require
publisher-specific setup.

Saved configurations are labelled **saved**, not verified connections.
An initialize/tools-list test must succeed before Kurt reports connected.
A failed test is reported as saved but failed; it is not a success receipt.
Catalog connection names retain the full publisher namespace.

## Composio

The menu provides the app's toolkit/authentication page, project API-key
dashboard, authentication documentation and Composio source repository.
If the project key is missing, Kurt asks for it in this flow. A newly
entered key is persisted after an auth config is successfully obtained.

Kurt first searches for enabled auth configs for that toolkit, including
custom configs created in the dashboard. Multiple configs require a choice.
Otherwise it attempts to create a managed config. Account authorization
uses `POST /api/v3.1/connected_accounts/link` and its returned browser URL.
Kurt polls the returned account ID and reports authorization active only
after observing `ACTIVE`; that is not proof that every app action works.
Custom app registration or unsupported authentication setup may still need
the provider/Composio dashboard. The fallback explains the supported auth
types rather than assuming every service needs an OAuth Client ID/Secret.

References: [Composio auth configs](https://docs.composio.dev/reference/api-reference/auth-configs),
[hosted links](https://docs.composio.dev/reference/api-reference/connected-accounts/postConnectedAccountsLink).

## Zapier and n8n

Each app submenu offers its integration/credential instructions and
**Connect platform MCP to Kurt**. Configure the app accounts and exposed
actions/workflows on the platform first. Then paste the platform's MCP
server URL and, if needed, access token into Kurt's hidden prompts.
Kurt tests the endpoint through the same MCP client used for other servers.
Opening an integration page alone does not connect anything to Kurt.

Direct commands: `/mcp platform zapier`, `/mcp platform n8n`.
The same commands are available as `kurt mcp platform <provider>`.

References: [Zapier setup](https://docs.zapier.com/mcp/quickstart),
[n8n MCP access](https://docs.n8n.io/connect/connect-to-n8n-mcp-server/).

## Verification — 2026-11-14

Inspected all bundled directory records: 58,869 MCP entries, 1,633 Composio
toolkits, 10,090 Zapier apps and 2,635 n8n integrations. With publisher or
package links, 56,427 MCP entries have a setup page; 2,442 have no such
published page. 3,117 have no connection recipe. These are catalog metadata
checks, not live verification of those services or their links.

All 271 tests passed outside the restricted sandbox. Connector tests cover
picker keyboard interaction, staying in the menu after opening a page,
missing recipes, recipe variants, placeholder resolution, cancellation,
credential handling, failed connection claims, namespace routing, Composio
custom-config reuse and hosted links. Existing protocol tests initialize and
call local stdio/HTTP/SSE fixture servers and exercise OAuth callbacks.
External service account sign-ins were not performed in this change.
