# Kurt browser extension (Manifest V3)

Reuses `web/src`'s chat UI (`App.tsx`, `AuthForm.tsx`, `Chat.tsx`,
`index.css`) directly via relative imports — editing those files updates
both the web app and this extension's popup. Only the auth transport
differs: the web app uses an HttpOnly cookie; this extension uses a bearer
token held in `chrome.storage.local` (see `src/tokenStore.ts` and
`web/src/api-client/client.ts`'s module docstring for why a cookie can't
work from a `chrome-extension://` origin — `SameSite=Strict` never sends
cross-site, and that origin always counts as cross-site).

## Build and load it locally

```sh
cd extension
npm install
npm run build
```

Then in Chrome: `chrome://extensions` → enable Developer mode → **Load
unpacked** → select `extension/dist`.

Before that works, a `kurt/saas` API instance must be reachable at the
origin listed in `manifest.json`'s `host_permissions` (default
`http://localhost:8099/*`, matching `web/README.md`'s local dev instructions)
— Chrome extensions get cross-origin `fetch` to a declared `host_permissions`
origin without needing any server-side CORS configuration, unlike a regular
web page.

## Before shipping this anywhere real

- `manifest.json`'s `host_permissions` and the popup's `VITE_KURT_API_URL`
  must both point at your real deployed API origin (HTTPS), not localhost.
- No icons are bundled yet — Chrome shows its default placeholder; add a
  real `icons` set in `manifest.json` before a Chrome Web Store submission.
- Not reviewed for a store listing (privacy policy, permissions
  justification, etc.) — that's separate from the code itself.
