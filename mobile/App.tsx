/**
 * Kurt mobile app — thin client over kurt/saas's hosted API, same contract
 * as web/ and extension/ (see web/src/api-client/client.ts). This is a
 * Phase 4 scaffold: signup/login + chat only. IAP (App Store/Play/Huawei
 * AppGallery) is not wired in yet — see mobile/README.md.
 *
 * @format
 */

import React, { useEffect, useState } from 'react';
import { ActivityIndicator, StatusBar, StyleSheet, useColorScheme, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ApiError, Tenant, createKurtClient } from '../web/src/api-client/client';
import { asyncStorageTokenStore } from './src/tokenStore';
import AuthScreen from './src/AuthScreen';
import ChatScreen from './src/ChatScreen';

// Platform-specific localhost addressing for local dev against a kurt/saas
// instance running on the same machine as this bundler:
//   - iOS Simulator: http://localhost:8099 (shares the host's network stack)
//   - Android Emulator: http://10.0.2.2:8099 (10.0.2.2 is the emulator's
//     alias for the host machine — localhost inside the emulator is the
//     emulator itself, not your Mac)
//   - A real device: neither works — use your machine's LAN IP or a
//     deployed HTTPS origin instead.
// See mobile/README.md for how to override this without editing the file.
const DEFAULT_BASE_URL = 'http://localhost:8099';

const client = createKurtClient({ baseUrl: DEFAULT_BASE_URL, tokenStore: asyncStorageTokenStore });

function KurtApp() {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [checkedSession, setCheckedSession] = useState(false);

  useEffect(() => {
    client
      .me()
      .then((response) => setTenant(response.tenant))
      .catch(() => setTenant(null))
      .finally(() => setCheckedSession(true));
  }, []);

  if (!checkedSession) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator />
      </View>
    );
  }

  if (!tenant) {
    return <AuthScreen client={client} onAuthenticated={setTenant} />;
  }

  return (
    <ChatScreen
      client={client}
      tenant={tenant}
      onLogout={async () => {
        try {
          await client.logout();
        } catch (error) {
          if (!(error instanceof ApiError)) throw error;
        }
        setTenant(null);
      }}
    />
  );
}

export default function App() {
  const isDarkMode = useColorScheme() === 'dark';
  return (
    <SafeAreaProvider>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
      <KurtApp />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  loading: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0f0f14' },
});
