# API key security audit — 2026-11-09

API keys had credible exposure paths. No exact matches of the eight currently configured secrets were found in 286 tracked files or 426 reachable Git-history blobs. This is not evidence that no historical disclosure occurred.

## Scope and evidence

Reviewed first-party credential loading/storage, provider requests, AI file tools, native bridge, agent execution, CLI delegation, MCP transports, conversation storage and generated artifacts. Exact-value scans also covered 879 bounded local runtime/state files; matches were confined to the expected `.kurt/.env` and MCP credential configuration. No key values or fragments are included here. Dependencies were not manually audited line by line.

The read-only scanner is reproducible with `python3 tools/security_audit.py`. It reports counts, matching tracked paths and file modes without printing values. It detects current configured values, not unknown/retired credentials, unreachable Git objects, remote logs or arbitrary encodings.

## Findings and changes

| Finding | Risk before changes | Change |
| --- | --- | --- |
| Child processes inherited all loaded provider credentials | High: a third-party CLI or MCP process could read unrelated keys directly from its environment | Base OS environment allowlist; explicit MCP per-server grants; Peekaboo receives no provider keys by default; managed OpenClaw receives Groq only; user-managed OpenClaw receives a bounded provider allowlist |
| Raw user/file/tool text could reach provider payloads and SQLite history | High: accidental pasted or echoed keys could be sent or retained | Shared known-secret, provider-token, credential-field and URL redaction; provider message boundaries; agent/MCP/native tool results; CLI results; history writes/reads; generated artifacts; primary streaming display |
| AI file tools could directly open credential files | High | Deny common credential/private-state paths, including resolved symlink targets, in file tools and CSV/JSON loader |
| Local key store, MCP configuration and memory had mode 0644 | Medium: readable by other local users, subject to directory access | Existing three files changed to 0600; memory initialization and setup enforce private modes; setup writes atomically and quotes dotenv values |
| HTTP MCP client followed redirects with custom secret headers | High if a malicious/compromised server redirects to another origin | Disable unrestricted client redirects; installed MCP SDK handles same-origin redirects itself; legacy SSE uses SDK defaults with unrestricted redirects off |
| Replicate polling reused authentication on an API-returned URL without origin validation | High if an unexpected polling URL was supplied | Require HTTPS, api.replicate.com, normal TLS port and no URL userinfo before authenticated polling |
| Claude/Gemini slash prompts interpolated into shell double quotes | High: command substitution could execute through task text | Shell-quote task as one argument; redact task text; restrict shell child environment |
| Env variants and generated edit backups could be committed | Medium | Ignore `.env.*` except explicit templates, and `*.kurt_bak` |
| Empty placeholder prefix always overrode exported environment credentials | Configuration integrity issue | Preserve real exports and parse quoted dotenv values correctly |

Actual provider authentication headers and intentionally configured MCP credentials remain intact. Redaction is applied to model content and output, not to the credentials needed to authenticate.

## Follow-up hardening

- Generated code, file execution, generic shell commands and AppleScript now use the macOS Seatbelt sandbox. Network access, Apple Events, Mach service lookup, process inspection, and reads/writes to the known credential roots/names are denied for the process and descendants. Symlink reads were tested. No unsandboxed retry occurs; unsupported hosts fail closed. These restrictions can prevent shell-based downloads and desktop automation; use the configured service adapters for intended network/desktop operations.
- OpenClaw, Peekaboo, Claude, Gemini, GitHub CLI and stdio MCP servers use a separate service profile that denies direct access to Kurt's key store and other common credential stores while retaining intended service networking. Own CLI login/state directories are allowed where needed. Trusted CLIs are launched as argument arrays, not shell command strings.
- Cloud screenshot analysis is disabled unless `KURT_ALLOW_CLOUD_VISION=1` is explicitly set. The background watcher never falls back to cloud, even with that opt-in, and no longer attaches screenshot bytes to emitted events/history.
- Remote MCP endpoints must use HTTPS; plain HTTP is restricted to literal loopback hosts. URL userinfo is rejected. This applies both at import and at connection time.
- New cron entries reference validated task IDs rather than embedding prompts or task names in shell commands. Schedule storage is redacted/private and cron logs use a restrictive umask. Existing crontabs were not rewritten. Voice-command logs redact known secrets.
- Updated OpenClaw's bundled npm dependency from 12.2.1 to 12.2.2 with lifecycle scripts disabled. A fresh registry audit reports **0 high, 0 critical and 33 moderate** findings. Remaining root advisories concern glob cancellation and minimatch amplification; fixing bundled versions requires upstream/bundled dependency changes beyond the compatible npm patch. No forced downgrade or unverified major dependency override was applied.

## Remaining risks

- Desktop adapters and network-capable third-party tools remain trusted capabilities. Their intended credentials/data can be used by the target service. IPC or a pre-existing desktop helper is not isolated by a file denylist. These profiles are defense in depth, not a separate OS identity or a full hostile-plugin containment boundary.
- Screenshots explicitly authorized for cloud vision can expose visible credentials; text redaction does not scrub image pixels. Explicit raw CLI arguments may appear in upstream logs/process arguments. Background cloud fallback is now blocked.
- Redaction and common credential-path rules are not exhaustive. Unknown filenames, short secrets, custom encodings, external backups and programs launched independently of Kurt remain outside these protections. Complete separation of hostile code requires a separate OS account/container or VM with explicit mounts and network policy.
- The 33 moderate dependency advisories remain unresolved; do not interpret zero high findings as a clean dependency audit.
- No keys were revoked or rotated. This audit did not inspect provider access logs, remote repositories, external backups or unreachable Git objects and cannot determine whether someone previously obtained a key.

## Verification

Synthetic-secret regression tests cover exact and encoded values, structured fields/URLs, subprocess grants, credential-path symlinks, private file creation, SQLite persistence, provider payload redaction with authentication preserved, Peekaboo isolation, dotenv precedence and shell task quoting. No live provider calls or actual secret values are used in those tests.

Final verification: all 93 tests passed (`python3 -m unittest discover -s tests -q`), including 23 security regressions. Python compilation and `git diff --check` passed. The suite uses localhost HTTP/SSE fixtures; it required execution outside the filesystem sandbox for local socket binding.

Real post-hardening CLI probe: OpenClaw configuration validated and Peekaboo permissions probe succeeded under the service sandbox. The probe did not request a screenshot or model task.
