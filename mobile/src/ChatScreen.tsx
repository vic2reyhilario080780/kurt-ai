import React, { useState } from 'react';
import { FlatList, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { ApiError, ChatMessage, KurtClient, Tenant } from '../../web/src/api-client/client';

export default function ChatScreen({
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

  async function handleSend() {
    const text = draft.trim();
    if (!text || sending) return;
    // kurt/saas's /v1/chat is stateless (kurt/saas/protocol.py caps it at 24
    // messages / 32 KiB) — resend the full visible history each turn, same
    // contract web/src/Chat.tsx and the kurt cloud ask CLI command use.
    const next = [...messages, { role: 'user', content: text } as ChatMessage];
    setMessages(next);
    setDraft('');
    setError(null);
    setSending(true);
    try {
      const response = await client.chat(next);
      setMessages([...next, { role: 'assistant', content: response.result.content }]);
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === 'capability_unavailable'
          ? 'Walang naka-configure na Groq key sa server — local dev lang ito.'
          : 'May hindi inaasahang error.',
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={styles.topbar}>
        <Text style={styles.plan}>Plan: {tenant.plan}</Text>
        <Pressable onPress={onLogout}>
          <Text style={styles.link}>Log out</Text>
        </Pressable>
      </View>
      <FlatList
        style={styles.messages}
        data={messages}
        keyExtractor={(_, index) => String(index)}
        renderItem={({ item }) => (
          <View style={[styles.bubble, item.role === 'user' ? styles.bubbleUser : styles.bubbleAssistant]}>
            <Text style={styles.bubbleText}>{item.content}</Text>
          </View>
        )}
      />
      {error && <Text style={styles.error}>{error}</Text>}
      <View style={styles.inputRow}>
        <TextInput
          style={styles.field}
          placeholder="Magtanong kay Kurt…"
          placeholderTextColor="#666677"
          value={draft}
          onChangeText={setDraft}
          editable={!sending}
        />
        <Pressable
          style={[styles.sendButton, (sending || !draft.trim()) && styles.buttonDisabled]}
          onPress={handleSend}
          disabled={sending || !draft.trim()}
        >
          <Text style={styles.buttonText}>{sending ? '…' : 'Send'}</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f0f14', paddingTop: 48, paddingHorizontal: 16 },
  topbar: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  plan: { color: '#e8e8f0' },
  link: { color: '#a29bfe' },
  messages: { flex: 1 },
  bubble: { padding: 10, borderRadius: 10, marginBottom: 8, maxWidth: '85%' },
  bubbleUser: { alignSelf: 'flex-end', backgroundColor: '#6c5ce7' },
  bubbleAssistant: { alignSelf: 'flex-start', backgroundColor: '#2a2a35' },
  bubbleText: { color: '#fff' },
  error: { color: '#ff6b6b', marginBottom: 8 },
  inputRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  field: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#333340',
    borderRadius: 8,
    padding: 10,
    color: '#e8e8f0',
    backgroundColor: '#1a1a22',
  },
  sendButton: { backgroundColor: '#6c5ce7', borderRadius: 8, paddingHorizontal: 16, justifyContent: 'center' },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontWeight: '600' },
});
