# Kurt mobile app (React Native)

Shares `web/src/api-client/client.ts` directly via relative imports (see
`metro.config.js`'s `watchFolders`) — same wire contract as the web app,
browser extension, and desktop app. The UI itself (`App.tsx`,
`src/AuthScreen.tsx`, `src/ChatScreen.tsx`) is **not** shared with those —
React Native doesn't render HTML/DOM, so it needs its own `View`/`Text`/
`TextInput` components — only the API-calling logic and types are reused.

Auth is bearer-token (`src/tokenStore.ts`, backed by
`@react-native-async-storage/async-storage`), same reasoning as the
extension and desktop app: there's no cookie jar here at all.

## What this is (and isn't) yet

This is a Phase 4 **scaffold**: signup/login + chat, generated with the
official `@react-native-community/cli init` template (not hand-rolled native
projects, to avoid an unverifiable from-scratch Xcode/Gradle setup) and then
wired to the shared api-client.

**Not included yet**: App Store / Google Play / Huawei AppGallery in-app
purchase integration. Per the approved plan, that needs new backend receipt-
verification endpoints (`kurt/saas/iap_apple.py`, `iap_google.py`,
`iap_huawei.py` — not written yet) that verify each store's signed
notification and then call the existing `Store.grant()` — the same
subscription/plan primitive `kurt/saas/admin.py` already uses, not a new
entitlement system.

## What was actually verified in this environment, and what wasn't

This sandbox has no Xcode (only Command Line Tools) and no JDK — a real
iOS Simulator or Android emulator build was **not possible here**. What
*was* verified:

- `npx tsc --noEmit` — clean, and confirmed (via `--listFiles`) that
  `web/src/api-client/client.ts` is genuinely included and type-checked,
  not silently skipped.
- `npx jest` — `App.tsx` renders successfully in the React Native test
  renderer (including the `/v1/me` session check failing gracefully with
  no network, same as it would on a real device with no server reachable).

You'll need a Mac with Xcode (iOS) and/or Android Studio + a JDK (Android)
to actually build and run this on a simulator/emulator/device — see
<https://reactnative.dev/docs/set-up-your-environment> for the official
setup guide, then:

```sh
cd mobile
npm install
npm run ios      # or: npm run android
```

### Reaching a local kurt/saas server from a simulator/emulator

`App.tsx`'s `DEFAULT_BASE_URL` is `http://localhost:8099`, which only
works for the **iOS Simulator** (it shares your Mac's network stack). The
**Android Emulator** needs `http://10.0.2.2:8099` instead — `10.0.2.2` is
the emulator's alias for the host machine. A **real device** needs your
machine's LAN IP or a deployed HTTPS origin — `localhost` always means the
device itself. Edit `DEFAULT_BASE_URL` in `App.tsx` accordingly for now
(a proper `.env`/build-config split is future cleanup, not done yet).

## Before shipping this anywhere real

- AsyncStorage is not encrypted at rest — swap `src/tokenStore.ts` for
  `react-native-keychain` (iOS Keychain / Android Keystore) before
  production, same note as `desktop/`'s `localStorage` use.
- No app icons, splash screen, or bundle identifier review beyond the
  CLI template defaults (`com.kurtmobile` placeholder-style ids from the
  generator) — needs real branding before any store submission.
- IAP, as above, is not implemented.
- Requires: Apple Developer Program enrollment, a Google Play Console
  account, and a Huawei AppGallery Connect account — none of which an AI
  assistant can create on your behalf.
