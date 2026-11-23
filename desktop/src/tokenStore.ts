import type { TokenStore } from '../../web/src/api-client/client';

const KEY = 'kurt_token';

/**
 * localStorage inside a Tauri webview is isolated to this app (not shared
 * with any real website) — same reasoning as the browser extension's
 * chrome.storage.local (see extension/src/tokenStore.ts). Bearer mode is
 * needed here for the same reason it's needed there: Tauri's frontend is
 * served from a custom scheme (tauri://localhost), which counts as a
 * different site from the http(s) API origin, so a SameSite=Strict cookie
 * would never be sent.
 */
export const localTokenStore: TokenStore = {
  async get() {
    return localStorage.getItem(KEY);
  },
  async set(token) {
    if (token) {
      localStorage.setItem(KEY, token);
    } else {
      localStorage.removeItem(KEY);
    }
  },
};
