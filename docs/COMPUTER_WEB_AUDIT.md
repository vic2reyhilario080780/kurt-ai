# Computer and web capability audit — 2026-11-15

Kurt has real host desktop automation and an independent Playwright browser.
These are separate execution paths. A working tool does not guarantee that every
AI provider will plan a complete workflow correctly.

## Live evidence on this iMac

| Capability | Observed result |
| --- | --- |
| Host app activation from natural chat | Calculator and TextEdit opened; foreground process independently verified. |
| Contextual app follow-up | Passed in an earlier run; the final run failed after rate limits and invalid provider tool arguments. Not consistently reliable. |
| Host desktop input | Safari fixture passed real typing, Return, hover and scroll, with independent final-page evidence. This run used direct tools, not the AI planner. |
| Web automation | Real headless installed Chrome passed navigation, form fill, button click and final text/title observation, with calls from different worker threads. |
| Web fetch | Local redirects and relative links passed; external `https://example.com` returned HTTP 200 and title `Example Domain`. |
| Read-only conversation | The no-app-action case passed without tool calls. |

Peekaboo reported Screen Recording, Accessibility and Event Synthesizing ready.
The bundled Playwright browser was missing. Kurt now successfully uses installed
Chrome when appropriate. No browser installation or OS permission changes were
needed for this audit.

## Fixes implemented

- Desktop coordinate clicks stop when foreground focus cannot be verified.
- Legacy app activation uses the same verified `open_application` receipt and
  app-only completion rules. Legacy desktop mutations also require a declared
  task goal; browser navigation/click/type do too.
- Native provider prompts no longer embed a duplicate copy of the tool catalog.
  Streaming HTTP error bodies are read before quota handling, preserving the real
  error instead of masking it with `ResponseNotRead`.
- Playwright creation, actions and cleanup stay on one dedicated owner thread.
  Missing bundled Chromium can fall back to installed Chrome/Edge; explicit
  selection is available through `KURT_BROWSER_CHANNEL=chrome` or `msedge`.
- Browser actions return fresh page URL, title, links and visible controls.
  Exact-text clicks reject ambiguous matches instead of silently using the first.
- Web fetch allows HTTP(S), rejects embedded credentials, limits response bodies
  to 2 MiB, reports final redirected URL/status/content type and text truncation,
  resolves relative links, and rejects binary documents with an explicit error.
- `kurt chat --verbose` exposes execution receipts for diagnostics; verification
  scripts enable it explicitly.

## Reproduce

```sh
python3 tools/verify_desktop_input.py --live --browser Safari --direct --output /tmp/kurt-computer-direct.json
python3 tools/verify_web_capabilities.py --output /tmp/kurt-web-capabilities.json
python3 tools/verify_semantic_assistant.py --live --model auto --output /tmp/kurt-semantic-auto.json
python3 -m unittest discover -s tests -q
```

The last suite passed **332 tests**. Live reports are local temporary artifacts.
The semantic report is deliberately not an all-pass report: final case results
were app activation pass, editor activation pass, contextual follow-up fail,
and read-only conversation pass. Earlier Groq-only attempts hit request-size
and rate limits; prompt size and masked HTTP errors have been fixed, but provider
availability and malformed arguments remain practical limits.

## Further improvements

1. Add bounded planner recovery for malformed arguments and accurate diagnostics
   distinguishing quota, provider errors and missing credentials.
2. Add an opt-in persistent automation profile with a visible account/session
   indicator, so a user can sign in once. The current isolated browser does not
   inherit the user's normal Chrome/Safari login sessions.
3. Expand live fixtures to downloads/uploads, tabs, dialogs and multi-page
   workflows; then test AI planning against those same completion conditions.
4. Add element-based dragging and richer post-action checks for desktop apps
   whose Accessibility trees are incomplete. Coordinate fallback still needs
   stronger screenshot provenance; it is not equivalent to an AX element receipt.

Arbitrary authenticated sites, CAPTCHA handling, every installed app, and full
AI-driven long workflows were not established by this audit.
