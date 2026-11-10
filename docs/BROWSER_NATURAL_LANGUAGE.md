# Natural-language browser opening in actual chat

Fixed and verified on 2026-11-10. Restart an already-running Kurt process to
load the updated code.

The installed `/opt/homebrew/bin/kurt chat` entrypoint passed **8/8 live cases**,
including:

- `magbukas ka ng browser`
- `Can you open a browser?`
- `buksan mo nga yung Chrome`
- `please open Microsoft Edge`
- `paki open naman ng Safari`
- Natural requests opening unique local pages in Chrome, Edge, and Safari.

[Live report and screenshot paths](browser-natural-language-chat-verification.json).
Regression suite: **184 passed, 282 subtests passed**.

## Behavior

Simple, complete browser-opening requests go directly to the observed desktop
adapter in both chat and ask. They do not require a model decision, API key,
provider credits, or a website URL. Generic `browser` resolves the actual macOS
HTTPS default; named browsers use their canonical application names.

The parser handles Tagalog/English requests and common politeness words. It
does not consume a partial multi-step task or an explanatory/negated example.
More complex tasks still go to the AI tool loop. The desktop schema also now
supports `open_app` when no URL was supplied.

Kurt observes launch readiness, focuses the exact window with verification,
then observes again. Read-only readiness checks can repeat; launches do not.
For a requested URL, address-bar matching identifies the correct window,
including when Chrome also has a profile picker. A browser-controlled profile
chooser may remain visible for a plain Chrome-opening request; Kurt does not
select an account implicitly. Address verification is conservative and may
report an unverified result if the destination redirects to a different URL.

## What the live test establishes

The verifier sends actual natural-language input to the installed chat CLI and
keeps it alive while independently checking the desktop. It verifies a real
window, the foreground app, and a unique page title for navigation cases. It
uses a deliberately invalid model selection (`offline/browser-smoke`) to
exercise the direct path; no model responses or desktop actions are mocked.

`chat --no-memory` isolates synthetic conversations from user history. Piped
non-interactive chat does not start the optional microphone listener or screen
watcher. The verifier exits each chat only after desktop verification; otherwise
macOS can restore focus to the editor before the check. Its foreground query
uses a fresh process to avoid cached NSWorkspace activation notifications.

Earlier tests covered compound tasks through `ask`; they did not establish
these simple natural-language cases in the live interactive chat path. This
report supplies that missing evidence.

Reproduce explicitly (opens and focuses the installed browsers):

```sh
python3 tools/verify_browser_chat.py --live --output /tmp/kurt-browser-chat.json
```
