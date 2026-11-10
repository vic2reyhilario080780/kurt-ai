# Installed-browser autonomous execution test

Tested on 2026-11-10. Application bundle URL registrations identified three
installed web browsers in `/Applications`, `/System/Applications`, and the user's
`Applications` folder: Google Chrome, Microsoft Edge, and Safari. No browsers
were installed as part of this test.

Each live test submitted one natural-language request through the actual Kurt
CLI: open a new local page, type a unique code, click its verification button,
and check the resulting text. Browsers were tested sequentially. A separate
read-only observation checked the result after Kurt finished.

| Browser | Latest result | Evidence and limitation |
| --- | --- | --- |
| Safari | Passed | Unique typed code and final `AUTONOMOUS_OK` text independently observed in the Safari retry. |
| Google Chrome | Passed after fix | Three desktop action calls; independently observed `AUTONOMOUS_OK: KURT_AUTO_1317EC38`. |
| Microsoft Edge | Passed after fix | Three desktop action calls; independently observed `AUTONOMOUS_OK: KURT_AUTO_C7D2EA55` in a separate retry. |

Evidence: [Chrome success in the repaired batch](browser-autonomy-fixed-verification.json),
[Edge success on retry](browser-edge-fixed-verification.json), and
[Safari success on retry](browser-safari-retry-verification.json).
All three browsers have individually passed the autonomous task. They did not
all pass within one uninterrupted batch: provider rate limits interrupted the
Edge/Safari entries in that batch. Earlier failed reports are retained in
[the initial batch](browser-autonomy-verification.json).

## Fixes and diagnostics

- Desktop routing now recognizes full browser names including Google Chrome and
  Microsoft Edge. Routing coverage also includes common browser aliases; this
  does not mean those other browsers were installed or tested live.
- The Peekaboo bridge rejected Chromium observations with inconsistent
  window-title evidence. Caller-local `--no-remote` observation succeeded.
  Chromium desktop actions now use that provider consistently for observation,
  focus, typing, and clicks, retaining ordinary permission/target validation.
- Chromium's `AXEnhancedUserInterface` mode was disabled, so its accessibility
  tree omitted page controls. Kurt now activates this attribute for the exact
  running browser process before observation. This requests the app's page AX
  tree; it does not change macOS permissions, restart the browser, or enable a
  remote-debugging port. This mechanism is described in the
  [Chromium accessibility documentation](https://www.chromium.org/developers/design-documents/accessibility/).
- Native attribute-setting can return an AX error even when Chromium applied
  the change. Kurt checks the actual attribute readback before reporting the
  mode enabled. It uses fresh, deeper traversal for Chromium observations,
  which exposed Edge's input after the mode was activated. Focus verification
  uses the same traversal and provider as target discovery.
- Chromium activation requires the macOS PyObjC bindings, available through
  `pip install '.[desktop]'` or the platform-conditional requirements file.
  When bindings or permissions are unavailable, Kurt reports activation status
  and retains its exact-target guards.
- The test verifier now handles null observation data rather than aborting the
  entire browser batch on a failed observation.

Regression suite: **167 passed, 264 subtests passed**. These results establish
the tested local-page behavior, not every website or browser feature.

Reproduce explicitly (model requests and desktop actions):

```sh
python3 tools/verify_desktop_autonomy.py --live --all-installed --output /tmp/browser-report.json
python3 tools/verify_desktop_autonomy.py --live --browser 'Google Chrome' --output /tmp/chrome-report.json
```
