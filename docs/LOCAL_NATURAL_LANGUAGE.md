# Local natural-language actions

Verified on 2026-11-10 through the installed `kurt chat` command, with a
deliberately invalid model selection. The supported simple requests execute
locally without an AI generation call. Restart an existing Kurt session to load
the changes.

## Live results

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
  native window observation and focus verification. The live app coverage is
  Calculator and TextEdit, in addition to the separately verified browsers;
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

Reproduce explicitly (opens apps, reads Mail counts, briefly plays Music):

```sh
python3 tools/verify_local_actions.py --live --output /tmp/kurt-local-actions.json
```
