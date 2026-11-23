# Kurt desktop app (Tauri)

Reuses `web/src`'s chat UI directly via relative imports (`App.tsx`,
`AuthForm.tsx`, `Chat.tsx`, `index.css`) — same reuse pattern as
`extension/`. Auth is bearer-token (held in the webview's `localStorage`,
see `src/tokenStore.ts`), not the web app's cookie — a Tauri window is
served from a `tauri://` origin, which counts as cross-site from the API's
point of view, so a `SameSite=Strict` cookie is never sent, same reasoning
as the browser extension.

## What's different from the web app: the "local bridge"

`src/LocalBridge.tsx` calls a Rust command (`run_kurt_cli` in
`src-tauri/src/lib.rs`) that shells out to the **already installed** `kurt`
CLI in its normal one-off-prompt mode (`kurt "<prompt>"`, stdin closed so it
exits after one reply — verified with `kurt "..." < /dev/null`). This is the
"local bridge" from the approved plan: real desktop control (open apps,
files, computer_use, agent tool-calling) reuses kurt's own existing, tested
capabilities instead of a new automation implementation in Rust/JS.

## Build and run it locally

```sh
cd desktop
npm install
npm run tauri dev     # hot-reload dev window
# or:
npm run tauri build --no-bundle   # just the native binary, no installer packaging
```

Verified in this session: `npx tsc`, `npx vite build`, and a full
`npx tauri build --no-bundle` all complete cleanly, producing a real
`src-tauri/target/release/desktop` Mach-O binary that launches and stays
running (process-liveness checked; a window may genuinely appear on
screen when you run it — that's expected, not a bug).

A `kurt/saas` API instance must be reachable at `VITE_KURT_API_URL`
(default `http://localhost:8099`, same as `web/`) for signup/login/chat to
work. The `kurt` command itself must be on `PATH` (the normal `pip install`
entry point) for the Local Bridge panel to work.

## Before shipping this anywhere real

- No code signing / notarization (macOS) or installer packaging configured
  — `--no-bundle` was used here on purpose to skip that. `bundle.targets`
  in `src-tauri/tauri.conf.json` is currently `"all"`; review per-OS signing
  requirements before producing a distributable installer.
- The Local Bridge panel runs whatever `kurt` is on `PATH` with no
  additional per-action consent prompt beyond kurt's own — reasonable for a
  single-user desktop app the user installed themselves, but worth a second
  look before this app is ever distributed to someone else's machine.
