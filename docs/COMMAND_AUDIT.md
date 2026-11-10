# Kurt command audit

Checked on 2026-11-10 against the local working tree.

## Results

- Latest full suite: `python3 -m pytest -q` — **196 passed, 302 subtests passed**.
- All **171 registered command/group entries** accept `--help` successfully.
- The suite executes all **30,000 native workflow fixture cases** and checks their results against expected facts.
- Additional local command checks passed: `version`, `library stats`, `library search`, `library show`, `read --lines`, `ls`, `grep`, and `find`.
- Integration tests cover desktop CLI argument forwarding, failures/timeouts/output limits, MCP stdio/HTTP/SSE fixture servers, coding read/edit/test execution, secret isolation, and SaaS controls.
- Two live autonomous Safari tasks passed from natural-language requests, with different input/button labels and unique test codes; independent observations verified both results. See [desktop verification](DESKTOP_CLI.md#autonomous-natural-language-test-2026-11-10).

## Bug fixed

The README advertised `kurt "task"`, `kurt --skill seo "task"`, and
`kurt --model gpt4o "task"`, but the root CLI rejected these as an unknown
command or option. The root command group now routes prompt shorthand to
`ask`, preserving its existing options and validation. Named commands retain
their normal routing. Use `kurt ask "hello"` when a prompt is also a command
name, and `kurt -- "-literal prompt"` when a prompt begins with a dash.

`tests/test_cli_commands.py` checks shorthand parsing, explicit commands,
invalid options, and help for the complete command tree without making model
requests.

## Verification limits

Passing help checks establish registration and parsing, not full execution of
every command. Integration fixtures do not prove that every live provider,
account, hosted service, browser action, or macOS desktop action works. This
audit did not send messages, publish content, change connected accounts, or
exercise every interactive setup wizard. Live integration checks still depend
on credentials, service availability, and operating-system permissions.

The first suite run inside the restricted tool sandbox reported 22 failures
from blocked nested macOS sandbox execution, localhost sockets, process
inspection, and artifact writes. With permission to run outside that outer
sandbox, all existing tests passed before the fix; the final expanded suite
also passed. Kurt's execution security checks remain enabled.
