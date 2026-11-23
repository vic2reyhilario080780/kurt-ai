import { useEffect, useState } from 'react';
import { ApiError, KurtClient, Tenant, createKurtClient } from './api-client/client';
import AuthForm from './AuthForm';
import Chat from './Chat';

const defaultClient = createKurtClient({
  baseUrl: import.meta.env.VITE_KURT_API_URL ?? 'http://localhost:8099',
});

/**
 * `client` is injectable so this exact component can be reused by the
 * browser extension (and, later, mobile) with a bearer-token client instead
 * of the web app's default cookie-based one — see web/src/api-client/client.ts
 * and extension/src/popup/main.tsx.
 */
export default function App({ client = defaultClient }: { client?: KurtClient }) {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [checkedSession, setCheckedSession] = useState(false);

  useEffect(() => {
    client
      .me()
      .then((response) => setTenant(response.tenant))
      .catch(() => setTenant(null))
      .finally(() => setCheckedSession(true));
  }, [client]);

  if (!checkedSession) {
    return <p>Loading…</p>;
  }

  if (!tenant) {
    return (
      <AuthForm
        client={client}
        onAuthenticated={(authenticatedTenant) => setTenant(authenticatedTenant)}
      />
    );
  }

  return (
    <Chat
      client={client}
      tenant={tenant}
      onLogout={async () => {
        try {
          await client.logout();
        } catch (error) {
          // Logout failing server-side still clears local UI state; the
          // cookie/token will simply expire on its own (SESSION_DAYS in app.py).
          if (!(error instanceof ApiError)) throw error;
        }
        setTenant(null);
      }}
    />
  );
}
