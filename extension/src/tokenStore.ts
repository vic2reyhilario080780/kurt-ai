import type { TokenStore } from '../../web/src/api-client/client';

const KEY = 'kurt_token';

/**
 * chrome.storage.local is isolated per-extension and unreachable from any
 * web page's JS (unlike localStorage on a normal page, which XSS on that
 * page could read) — a reasonable place for a bearer token in an extension
 * context, the same tradeoff every browser-extension client makes.
 */
export const chromeTokenStore: TokenStore = {
  async get() {
    const result = await chrome.storage.local.get(KEY);
    return typeof result[KEY] === 'string' ? result[KEY] : null;
  },
  async set(token) {
    if (token) {
      await chrome.storage.local.set({ [KEY]: token });
    } else {
      await chrome.storage.local.remove(KEY);
    }
  },
};
