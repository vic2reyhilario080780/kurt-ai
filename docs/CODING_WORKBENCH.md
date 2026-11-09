# Kurt coding workbench

Kurt now has an executable coding workflow and an optional installed-Codex backend. This transfers tool access and orchestration patterns, **not OpenAI's model weights, private tools, accounts or a guarantee of identical reasoning quality**.

## What is wired

| Capability | Implementation |
| --- | --- |
| Understand a repository | Workspace-scoped read/list/grep/find tools; root AGENTS.md loaded into the task |
| Make changes | Exact edits, multi-edit and file creation with credential-path and symlink checks |
| Run and verify | Exact command arrays, actual exit codes, bounded output, timeouts and process-group cleanup |
| Inspect Git | Fixed read-only status/diff/log broker; no external diff/textconv, pager, hooks, fsmonitor, network or repository writes |
| Use provider-native tools | JSON schemas now cover the complete 49-tool agent registry rather than only the six data/desktop bridge tools |
| Keep model payloads usable | Dedicated coding tool profile, bounded tool previews/history, and bounded rate-limit recovery |
| Work on the intended repo | Per-task workspace context propagates across async/thread boundaries without global chdir |
| Reuse project skills | Discover/read SKILL.md under .agents/skills, .skills and skills; scripts are not automatically executed |
| Use MCP | On-demand server tool discovery and existing authenticated MCP execution; task startup no longer starts every server |
| Run background tasks | Existing process manager now uses the same OS sandbox, private log files, concurrent-process cap and file-size limit |
| Delegate to Codex | Explicit codex_task, delegate_cli with codex, /codex and kurt code --backend codex |
| Plan, research and desktop workflows | Existing planning, subagent, web, vision, browser and desktop tools remain in the general agent registry; availability depends on configuration and permissions |

No customer-host shell or desktop control was added to the SaaS API. The hosted foundation still accepts only its bounded chat/native endpoints.

## Use it

```sh
kurt code 'Find and fix the failing authentication test' --cwd /path/to/repo
kurt code 'Review and refactor this module' --cwd /path/to/repo --steps 40
kurt code 'Fix the failing tests' --cwd /path/to/repo --check '["python3","-m","pytest","-q"]' --output ./coding-report.json
kurt code 'Implement the requested feature' --cwd /path/to/repo --backend codex
```

The native backend uses Kurt's configured model routing. The Codex backend requires an installed supported Codex CLI and its own authorized login/API access. In chat, `/codex status` checks that setup and `/codex <task>` defaults to read-only delegation. Writing delegation is explicit through `kurt code --backend codex` or the codex_task tool's workspace-write mode.

The report distinguishes task completion from check results (`passed`, `failed`, `not_run`) and Git review availability. It preserves pre-existing Git status and shows the final working-tree diff without staging, committing or resetting anything. Git diff includes tracked working-tree changes, not untracked file contents; inspect the status and files as well. A zero exit code proves that the listed command succeeded, not that every possible test or security property was verified.

## Security boundaries

Generated commands retain the credential-path deny rules and disabled networking/IPC. Writes are limited to the active workspace and system temporary directories. Direct file tools reject paths and resolved symlinks outside the workspace. These controls are for the current macOS host; they are not a general multi-tenant sandbox or a completed Windows/Linux native execution implementation.

Git inspection is a separate fixed-command broker: macOS Git needs OS IPC/process metadata to initialize. That broker keeps networking, ordinary file writes and credential reads blocked, with only /dev/null writes allowed. It accepts only status, diff and recent log inspection. Generic generated code does not receive the broker's privileges.

Codex enforces its own native permission profile rather than being nested inside a second Seatbelt sandbox. The adapter selects read-only/workspace permissions, disables command networking, denies credential roots/environment files, reads only needed runtime/workspace paths, filters inherited credentials, sends the redacted task via stdin and requests ephemeral JSONL execution. No sandbox bypass flag or unsafe fallback is used. Legacy project sandbox settings that could override the profile are rejected. The profile was tested against the installed Codex CLI with synthetic files. Consult the official [permission profile documentation](https://learn.chatgpt.com/docs/permissions) and [non-interactive execution documentation](https://learn.chatgpt.com/docs/non-interactive-mode).

A Codex turn is not called completed solely because its process exits zero: a completed turn and final agent message must be present, without an error/failed-turn event. Reported edits remain distinct from independently verified changes. Timeout/output-limit results may leave partial edits and are never retried automatically.

## Verification and limits

- Regression tests perform a real file-read/edit/test cycle in a disposable selected workspace, verify the provider receives coding schemas, test malformed/nested requests, load a project skill, reject symlink escapes and out-of-workspace writes, bound process output, filter keys and execute the installed Codex permission sandbox.
- A live Kurt model test used its configured Groq gpt-oss-120b routing on a synthetic arithmetic repository. It read both files, changed subtraction to addition and ran a real passing unit test. Rate-limit recovery was exercised. Its original Git inspection hit a sandbox startup failure; the Git broker was subsequently corrected and verified with real restricted subprocess tests. No production repository files were changed by the live model.
- Codex login/status and its actual permission sandbox were checked. The external Codex model coding turn was covered with event/argument fixtures, not a live delegated model call. This is not evidence that every Codex feature or every model works identically.
- Model quality, quotas, external account credentials, OS permissions and installed dependencies still matter. Project/MCP/skill content is not automatically trustworthy. Existing data-library recipes remain deterministic recipes, not 30,000 independent coding algorithms.
- Full parity with every connected app, proprietary hosted tool, image/document workflow, long-lived Codex session or future Codex feature is not claimed. Those require their own adapters, permissions and validation. Your personal Codex login is not automatically a subscription entitlement for Kurt's SaaS customers.

Final local verification: 141 project tests passed, including 16 coding-workbench tests. The final Codex credential-profile change was additionally checked by rerunning all 16 workbench tests. Python compilation and git diff whitespace checks passed.
