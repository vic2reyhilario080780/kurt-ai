# DeepSeek agent and CLI setup — 2026-11-17

Kurt now connects both tools already installed on this iMac. They are separate
community packages, not the same executable or an assertion of an official
DeepSeek CLI distribution:

| Kurt choice | Installed tool | Version |
| --- | --- | --- |
| `deepseek` | Python `deepseek_agent` / `deepseek_cli` package | 0.6.6 |
| `deepseek-cli` | Node `deepseek-terminal-cli` | 1.3.0 |

No package was installed or upgraded. Existing Chat AI and CLI defaults were not
changed. The independent native DeepSeek API chat route remains available.

## Shared setup

Both adapters require the current `DEEPSEEK_API_KEY` from Kurt `/setup`
(`~/.kurt/.env`). Missing/blank setup blocks inference before process launch;
inherited terminal keys, community-package embedded keys and their saved login
files are not used as fallback. Rotation takes effect on the next request.
Only the configured provider key is passed to the Terminal CLI. The Python agent
also receives the configured `TAVILY_API_KEY` if available; otherwise its Tavily
key is deliberately unset via a noncredential sentinel rather than a bundled key.
No other provider/GitHub keys are forwarded.

Both use the official `https://api.deepseek.com` endpoint and `deepseek-flash`
model. The native Chat AI picker also offers `deepseek-v4-pro`.
[DeepSeek's current model/endpoint documentation](https://api-docs.deepseek.com/quick_start/pricing/).

## Use in Kurt

- `/setting` → CLI → `deepseek` (DeepSeek Agent, Python), or `deepseek-cli`
  (DeepSeek Terminal CLI, Node).
- `/cli default deepseek` or `/cli default deepseek-cli` saves that CLI and
  applies it to this chat. The next welcome banner reflects the saved choice.
- `/deepseek <task>` and `/deepseek-cli <task>` run one explicit task without
  changing the selected default. Results remain available to follow-up chat.
- `/cli probe deepseek` / `/cli probe deepseek-cli` check installed versions
  without inference; `/cli test <name>` performs one minimal paid API reply test.
- Outside chat, use `kurt cli probe <name>` and `kurt cli test <name>`.
- For native DeepSeek Chat AI with Kurt's own tools: `/cli use auto`, then
  `/model deepseek-flash deepseek`. To save it, use
  `/model default deepseek-flash deepseek` or the Chat AI settings picker.
- The agent's `delegate_cli` tool accepts both names when orchestration is
  enabled. Existing pinned-default orchestration rules are preserved.

## Adapter behavior and limits

The Python package's top-level CLI adds automatic tests/bug-fix follow-ups even
for simple questions. Kurt instead calls its installed public `AgentOptions` /
`agent_loop` API in the Python runtime named by its console entry point, with
no extra follow-ups. It supplies read-only/workspace-limited options, at most
8 steps, a private temporary transcript and an explicit non-thinking API request.
That avoids losing required reasoning history in this older package's tool-call
replay. A final assistant transcript entry is required for a completed reply.
SDK retries are disabled.

The Node CLI receives the prompt via stdin with `CI=1`, at most 8 steps and no
`--yes` flag. Its piped implementation can execute tools without prompting, so
absence of `--yes` alone is **not** a read-only guarantee. The macOS kernel
sandbox denies filesystem writes except inside the adapter's private runtime
directory (plus `/dev/null`), and denies Apple events. Both adapters use that
restriction, a temporary HOME, the existing credential-path deny rules and
bounded process-group cleanup. Standalone CLI configurations are not edited.
These are filesystem restrictions, not proof of every possible external effect
of a trusted third-party CLI with network access.

Node CLI responses are brief (its upstream renderer only emits the first line
of ordinary assistant content). Tool workflows require its final `finish`
summary; step-limit output and absent final answers fail even if upstream exits
zero. For full-length chat use native DeepSeek API chat or the Python agent.
No adapter automatically repeats an indeterminate task. Image-byte forwarding
and writable coding sessions are not supported through these defaults.
The enforced filesystem sandbox currently supports these adapters on macOS;
unsupported hosts fail closed.

## Validation and current blocker

The isolated full suite passed **419 tests**, and the final focused run passed
**64 tests**. Both version probes passed. Against a local OpenAI-protocol fixture, both
installed tools completed a two-request file-read/tool-reply round trip with
exact synthetic key/model forwarding. Separate forced shell-write tests left
the temporary project file unchanged. The Python payload explicitly disabled
thinking. Reports contain only synthetic data; no paid endpoint was used.

The live Terminal CLI test reached DeepSeek but returned **HTTP 402 / Insufficient
Balance**. The initial live Python-agent reply test also failed without a verified
reply. No live completion is claimed for either adapter. Requests were not
repeated after the balance blocker. Add API balance in the
[DeepSeek platform](https://platform.deepseek.com/), then run the explicit test
commands before relying on live work. Installation/version status does not
verify credits, model availability or successful reasoning.

Reproduce local transport/tool/sandbox verification with
`PYTHONPATH=. python3 tools/verify_deepseek_adapters.py --output /tmp/deepseek-verification.json`.
