import { FormEvent, useState } from 'react';
import { ApiError, KurtClient, Tenant } from './api-client/client';

const ERROR_MESSAGES: Record<string, string> = {
  invalid_credentials: 'Mali ang email o password.',
  email_taken: 'May account na gamit ang email na ito.',
  invalid_signup: 'Tsekin ang email (valid format) at password (8+ characters).',
  invalid_login: 'Tsekin ang email at password.',
  rate_limited: 'Sobra-sobra na ang attempts — subukan ulit mamaya.',
  network_error: 'Hindi ma-reach ang server. Tumatakbo ba ang kurt.saas.app lokal?',
};

function friendlyError(error: unknown): string {
  if (error instanceof ApiError) {
    return ERROR_MESSAGES[error.code] ?? `Error: ${error.code}`;
  }
  return 'May hindi inaasahang error.';
}

export default function AuthForm({
  client,
  onAuthenticated,
}: {
  client: KurtClient;
  onAuthenticated: (tenant: Tenant) => void;
}) {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = mode === 'login' ? await client.login(email, password) : await client.signup(email, password);
      onAuthenticated(response.tenant);
    } catch (submitError) {
      setError(friendlyError(submitError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="kurt-card">
      <h1>Kurt</h1>
      <p>{mode === 'login' ? 'Mag-login para magpatuloy.' : 'Gumawa ng bagong account (trial plan).'}</p>
      {error && <div className="kurt-error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <input
          className="kurt-field"
          type="email"
          placeholder="email@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <input
          className="kurt-field"
          type="password"
          placeholder="password (8+ characters)"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          minLength={8}
          required
        />
        <button className="kurt-button" type="submit" disabled={busy}>
          {busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Sign up'}
        </button>
      </form>
      <p>
        {mode === 'login' ? 'Wala pang account?' : 'May account ka na?'}{' '}
        <button
          type="button"
          className="kurt-link-button"
          onClick={() => {
            setMode(mode === 'login' ? 'signup' : 'login');
            setError(null);
          }}
        >
          {mode === 'login' ? 'Sign up' : 'Log in'}
        </button>
      </p>
    </div>
  );
}
