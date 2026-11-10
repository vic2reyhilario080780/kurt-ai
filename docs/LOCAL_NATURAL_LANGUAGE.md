# Local natural-language actions

**Current chat architecture:** [goal-directed semantic assistant](SEMANTIC_ASSISTANT.md).
The model-free chat measurements below describe the preceding implementation.
Ordinary chat now uses model-selected tools and declared goals; the literal
local adapters remain available to quick `ask`/`do` and voice shortcuts.

Verified on 2026-11-10 through the installed `kurt chat` command, with a
deliberately invalid model selection. The supported simple requests execute
locally without an AI generation call. Restart an existing Kurt session to load
the changes.

## Live results

Follow-up app-opening fix: **6/6 requests passed in one persistent chat** in
[the native app report](app-opening-native-verification.json), using an invalid
AI model and a separate foreground observer after each request. Requests include
`buksan mo yung app na Calculator`, `mag open ka ng TextEdit`,
`buksan mo ang Notes sa imac ko`, `open the Calculator app`, and
`paki bukas ng TextEdit`. Calculator, TextEdit and Notes all became foreground.
Final regression: **203 tests and 314 subtests passed**.

All **7/7 cases passed** in the [live verification report](local-natural-language-verification.json):

| Request | Independently verified result |
| --- | --- |
| `buksan mo nga yung Calculator` | Calculator window observed after opening. |
| `Can you open TextEdit?` | TextEdit window observed after opening. |
| `i-check mo ang email ko` | Apple Mail account/unread counts matched the reply; one configured account and zero unread at test time. |
| `magpatugtog ka ng musika` | Native Music player state changed to `playing`. Playback was paused after testing if it had initially been inactive. |
| `i-download mo ang URL sa "output-path"` | Synthetic HTTP file saved with the exact expected bytes and SHA-256. |
| Same download to an existing destination | Refused; existing bytes preserved. |
| `i-download mo ito` without a source | Requested the direct download link; no invented file or source. |

## Supported scope

- App opening resolves exact installed application names and common aliases,
  using the same Tagalog/English opening grammar as browser requests. It uses
  macOS LaunchServices to open/reopen the app and verifies its exact running
  process is active and foreground. Simple non-browser app opening no longer
  requires Peekaboo, screen capture or Accessibility permissions. AppKit's run
  loop is pumped so successive requests see current foreground state. The live
  app coverage is Calculator, TextEdit and Notes, alongside the separate browsers;
  it is not a claim that every installed app has been tested.
- Email checking currently reads **Apple Mail unread counts**, not message
  bodies or attachments. It neither sends replies nor changes read flags. An
  empty/unconfigured account is reported as setup needed. Gmail/Outlook web
  accounts and content summarization require their own integration and tests.
- Generic Music requests resume a paused track, preserve active playback, or
  select an available local audio track when the queue is stopped. Up to the
  first 32 library file tracks are checked for availability. Named-song search
  and Spotify are not implemented by this direct adapter. An unavailable
  track or missing library produces a request for more information.
- Downloads require an explicit HTTP(S) URL. Output defaults to `~/Downloads`
  or the supplied filename. The action has a **10-MiB cap**, time/read budgets,
  and no-overwrite publication. It does not open, execute or install downloaded
  files. Authenticated browser downloads are outside this direct HTTP adapter.
- The parser only consumes complete simple requests. Compound tasks continue
  through the existing AI flow; their completion is not established here.
- Simple requests use the same direct executor in chat, ask, do and standalone
  voice. Voice routing is regression-tested with transcribed text; this follow-up
  did not record microphone input. Expanded grammar still rejects explanations,
  negations and compound actions rather than partially executing them.

## Native integration

Mail and Music use fixed, allowlisted Apple Scripting Bridge selectors rather
than a generic script interpreter. Only Mail account/unread counts and Music
status/play/pause operations are accepted. Native Automation permissions still
apply, and an Apple-event error is reported as failure rather than an empty
inbox or successful playback. External CLI/generated-code sandboxes are
unchanged. See [Apple's Scripting Bridge reference](https://developer.apple.com/documentation/scriptingbridge/sbapplication).

macOS bindings are declared in `kurt-ai[desktop]` and the platform-conditional
requirements. No account settings, saved trusted directories, or system privacy
permissions were changed during the tests.

The verifier keeps real chat sessions alive while checking app/player state.
It serves a tiny synthetic file from a local HTTP server and checks the saved
bytes. It reads no email bodies and makes no mail/streaming-provider account
changes.

Historical verifier for the preceding model-free chat implementation:

```sh
python3 tools/verify_local_actions.py --live --output /tmp/kurt-local-actions.json
```

Historical app-only verifier (its `--observe` helper remains used by current tests):

```sh
python3 tools/verify_app_opening.py --live --output /tmp/kurt-apps.json
```

For current semantic chat, use `tools/verify_semantic_assistant.py --live --output /tmp/kurt-semantic.json`.
