# Kurt desktop execution

The current [semantic assistant architecture](SEMANTIC_ASSISTANT.md) supersedes
the keyword-routed chat flow and ambiguous desktop function schema discussed
below. Its semantic-goal and Safari workflow reports document the newer behavior;
older failure reports remain as historical evidence.

Kurt does not contain copies of Claude, Gemini or Codex model weights or private
agent implementations. It implements a local observe → act → observe loop using
the configured model for decisions and Peekaboo for macOS interaction.

In `kurt chat`, ask for the outcome in ordinary Tagalog or English. For example:

> Buksan ang Safari sa website na ito, ilagay ang text sa search box, pindutin
> ang Return, at tingnan kung lumabas ang hinahanap ko.

Simple browser/app opening still executes locally without model credits.
Compound desktop tasks use the model loop, bounded to 24 tool calls. Each input
uses a fresh non-dialog observation and an exact app/window. Available structured
actions are app/URL opening, observation, filling a uniquely labelled input,
clicking or moving the pointer to a uniquely labelled element, one keyboard
chord, and scrolling 1–20 units. Input is sent once; a dispatch receipt alone
does not establish that the requested result happened.

A compact action history survives removal of older screen observations from
the model context. Repeating an identical rejected tool request stops the loop
without invoking it again; a new provider call ID does not bypass this guard.

Text filling uses keyboard delivery so webpage input handlers receive actual
key events. Literal backslashes are escaped before passing text to Peekaboo.
Mouse targeting uses observed element IDs; coordinate guessing is unsupported
by this structured tool. Ambiguous targets and dialogs block input.

Groq is the primary desktop planner. If it fails, the configured OpenRouter
account can handle the pending workflow with its existing tool history.
Both providers receive function schemas and matching tool result IDs. Switching
providers resumes decisions without replaying completed actions. Provider quota
and credit limits still apply. A 429 is reported as a rate limit, rather than a
missing API key.

This is bounded desktop control, not proof of reliable execution in every app
or website. The model sees accessibility observations; this change does not
add cloud screenshot vision, unattended background scheduling, or arbitrary
OS command execution. Apps must expose accessible controls and macOS must allow
the existing desktop helper to interact with them.

Live verification uses a temporary local HTML page through the actual installed
`kurt chat`. Its title becomes `INPUT_OK` only after the exact typed code reaches
the page's Enter handler, mouse hover fires, and the page scrolls. The verifier
independently observes that title while chat remains alive. Reports retain
failures as well as successes. Reproduce one browser at a time:

```sh
python3 tools/verify_desktop_input.py --live --browser Safari --model openai/gpt-oss-120b --output /tmp/kurt-input.json
```

`--model openai/gpt-oss-120b` explicitly selects OpenRouter in chat. Omit it to
test automatic model routing. `--direct` isolates the tools without an AI planner.
See the `desktop-input-*-verification.json` reports beside this document for
actual outcomes; older browser click/open tests establish different scope.

Validation on 2026-11-10:

| Check | Result |
| --- | --- |
| Regression suite | 199 passed, 309 subtests passed |
| Chrome, actual natural-language chat | Passed all four effects and independently observed `INPUT_OK` |
| Safari, direct tool sequence after typing fix | Passed all four effects and independently observed `INPUT_OK` |
| Safari, actual natural-language chat | Incomplete: Groq quota interrupted the first run; the OpenRouter function-call run reached the 24-step bound |
| Edge, direct tool sequence | Passed all four effects and independently observed `INPUT_OK` |
| Edge, actual native-function chat | Incomplete: repeated target argument errors and restarts reached the step bound |
| Safari, final schema/guard chat check | Incomplete; duplicate invalid fill stopped before another invocation, as intended |

The Safari direct check also retained a failed focus-dispatch receipt: the URL
was observed, subsequent exact-window actions succeeded, and the final page
state passed. That is not evidence that every individual dispatch was verified.
Follow-up runs clarified argument descriptions and added the rejected-call guard;
the schema/ledger reports record their results independently. Direct checks do
not establish that an AI planner can complete the same workflow reliably.

Restart an already-running Kurt session after updating its Python source.
