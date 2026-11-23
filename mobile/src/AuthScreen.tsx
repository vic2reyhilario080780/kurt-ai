import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { ApiError, KurtClient, Tenant } from '../../web/src/api-client/client';

const ERROR_MESSAGES: Record<string, string> = {
  invalid_credentials: 'Mali ang email o password.',
  email_taken: 'May account na gamit ang email na ito.',
  invalid_signup: 'Tsekin ang email (valid format) at password (8+ characters).',
  invalid_login: 'Tsekin ang email at password.',
  rate_limited: 'Sobra-sobra na ang attempts — subukan ulit mamaya.',
  network_error: 'Hindi ma-reach ang server. Tama ba ang API base URL mo?',
};

function friendlyError(error: unknown): string {
  if (error instanceof ApiError) return ERROR_MESSAGES[error.code] ?? `Error: ${error.code}`;
  return 'May hindi inaasahang error.';
}

export default function AuthScreen({
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

  async function handleSubmit() {
    setBusy(true);
    setError(null);
    try {
      const response = mode === 'login' ? await client.login(email, password) : await client.signup(email, password);
      onAuthenticated(response.tenant);
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setBusy(false);
    }
  }

  const disabled = busy || !email || password.length < 8;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Kurt</Text>
      <Text style={styles.subtitle}>
        {mode === 'login' ? 'Mag-login para magpatuloy.' : 'Gumawa ng bagong account (trial plan).'}
      </Text>
      {error && <Text style={styles.error}>{error}</Text>}
      <TextInput
        style={styles.field}
        placeholder="email@example.com"
        placeholderTextColor="#666677"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="email-address"
      />
      <TextInput
        style={styles.field}
        placeholder="password (8+ characters)"
        placeholderTextColor="#666677"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />
      <Pressable style={[styles.button, disabled && styles.buttonDisabled]} onPress={handleSubmit} disabled={disabled}>
        {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>{mode === 'login' ? 'Log in' : 'Sign up'}</Text>}
      </Pressable>
      <Pressable
        onPress={() => {
          setMode(mode === 'login' ? 'signup' : 'login');
          setError(null);
        }}
      >
        <Text style={styles.link}>{mode === 'login' ? 'Wala pang account? Sign up' : 'May account ka na? Log in'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 24, backgroundColor: '#0f0f14' },
  title: { fontSize: 32, fontWeight: '700', color: '#e8e8f0', marginBottom: 4 },
  subtitle: { color: '#a0a0b0', marginBottom: 16 },
  field: {
    borderWidth: 1,
    borderColor: '#333340',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    color: '#e8e8f0',
    backgroundColor: '#1a1a22',
  },
  button: { backgroundColor: '#6c5ce7', borderRadius: 8, padding: 14, alignItems: 'center', marginTop: 4 },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontWeight: '600' },
  error: { color: '#ff6b6b', marginBottom: 12 },
  link: { color: '#a29bfe', textAlign: 'center', marginTop: 16 },
});
