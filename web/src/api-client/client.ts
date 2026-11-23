/**
 * Thin, dependency-free client for kurt/saas's hosted API
 * (see docs/SAAS_FOUNDATION.md and kurt/saas/app.py for the exact contract).
 *
 * Deliberately framework-free (plain fetch) so this file can be reused as-is
 * by the browser extension and — via a React Native-compatible fetch — the
 * future mobile client, per the Phase 2-4 roadmap in the approved plan. Only
 * the UI layer differs per platform; this is the one place that knows the
 * wire format.
 *
 * Two auth transports, chosen by whether a TokenStore is supplied:
 *  - cookie (default, no tokenStore): the web app. Signup/login set an
 *    HttpOnly SameSite=Strict cookie server-side; the raw token is never in
 *    JS-reachable memory — see kurt/saas/app.py's _session_cookie.
 *  - bearer (tokenStore supplied): the extension and future mobile client.
 *    SameSite=Strict cookies are never sent cross-site, and a
 *    chrome-extension:// origin always is — so these callers get the raw
 *    token back in the JSON body instead and hold it themselves
 *    (chrome.storage.local, OS keychain, ...), sent as a normal
 *    Authorization: Bearer header, same as the existing CLI tokens.
 */

export interface Tenant {
  id: string;
  plan: string;
  active_until: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export class ApiError extends Error {
  constructor(public code: string, public status: number) {
    super(code);
    this.name = 'ApiError';
  }
}

export interface TokenStore {
  get(): Promise<string | null>;
  set(token: string | null): Promise<void>;
}

export interface KurtClientOptions {
  baseUrl: string;
  /** Omit for the web app's cookie flow; supply for bearer-token clients
   * (browser extension, mobile). */
  tokenStore?: TokenStore;
}

export function createKurtClient({ baseUrl, tokenStore }: KurtClientOptions) {
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(init.headers as Record<string, string> | undefined),
    };
    if (tokenStore) {
      const token = await tokenStore.get();
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    let response: Response;
    try {
      response = await fetch(baseUrl + path, {
        ...init,
        // Cookie mode needs this to send/receive kurt_session; bearer mode
        // never sets a cookie in the first place, so 'omit' changes nothing
        // except avoiding a pointless cross-site cookie attempt.
        credentials: tokenStore ? 'omit' : 'include',
        headers,
      });
    } catch {
      throw new ApiError('network_error', 0);
    }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new ApiError(typeof body.error === 'string' ? body.error : 'request_failed', response.status);
    }
    return body as T;
  }

  async function authenticate(path: '/v1/signup' | '/v1/login', email: string, password: string) {
    const payload: { email: string; password: string; client?: 'bearer' } = { email, password };
    if (tokenStore) payload.client = 'bearer';
    const result = await request<{ tenant: Tenant; token?: string }>(path, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (tokenStore && result.token) await tokenStore.set(result.token);
    return { tenant: result.tenant };
  }

  return {
    signup: (email: string, password: string) => authenticate('/v1/signup', email, password),
    login: (email: string, password: string) => authenticate('/v1/login', email, password),
    logout: async () => {
      const result = await request<{ status: string }>('/v1/logout', { method: 'POST' });
      if (tokenStore) await tokenStore.set(null);
      return result;
    },
    me: () => request<{ tenant: Tenant }>('/v1/me', { method: 'GET' }),
    chat: (messages: ChatMessage[]) =>
      request<{ request_id: string; result: { model: string; content: string } }>('/v1/chat', {
        method: 'POST',
        body: JSON.stringify({ messages }),
      }),
  };
}

export type KurtClient = ReturnType<typeof createKurtClient>;
