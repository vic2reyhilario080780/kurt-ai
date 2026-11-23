import { FormEvent, useState } from 'react';
import { ApiError, ChatMessage, KurtClient, Tenant } from './api-client/client';

export default function Chat({
  client,
  tenant,
  onLogout,
}: {
  client: KurtClient;
  tenant: Tenant;
  onLogout: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;
    const next = [...messages, { role: 'user', content: text } as ChatMessage];
    setMessages(next);
    setDraft('');
    setError(null);
    setSending(true);
    try {
      // kurt/saas's /v1/chat is stateless (kurt/saas/protocol.py caps it at
      // 24 messages / 32 KiB) — the full visible history is resent each
      // turn, same contract the kurt cloud ask CLI command already uses.
      const response = await client.chat(next);
      setMessages([...next, { role: 'assistant', content: response.result.content }]);
    } catch (chatError) {
      setError(
        chatError instanceof ApiError
          ? chatError.code === 'capability_unavailable'
            ? 'Walang naka-configure na Groq key sa server (KURT_SAAS_GROQ_KEY) — local dev lang ito.'
            : `Error: ${chatError.code}`
          : 'May hindi inaasahang error.',
      );
      setMessages(messages); // roll back the optimistic user message's follow-up state
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="kurt-card">
      <div className="kurt-topbar">
        <span>Plan: {tenant.plan}</span>
        <button type="button" className="kurt-link-button" onClick={onLogout}>
          Log out
        </button>
      </div>
      <div className="kurt-messages">
        {messages.map((message, index) => (
          <div key={index} className={`kurt-message ${message.role}`}>
            {message.content}
          </div>
        ))}
      </div>
      {error && <div className="kurt-error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <input
          className="kurt-field"
          placeholder="Magtanong kay Kurt…"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={sending}
        />
        <button className="kurt-button" type="submit" disabled={sending || !draft.trim()}>
          {sending ? 'Naghihintay…' : 'Send'}
        </button>
      </form>
    </div>
  );
}
