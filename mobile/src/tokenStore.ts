import AsyncStorage from '@react-native-async-storage/async-storage';
import type { TokenStore } from '../../web/src/api-client/client';

const KEY = 'kurt_token';

/**
 * Bearer mode, same reasoning as extension/desktop (see
 * web/src/api-client/client.ts's module docstring): React Native has no
 * cookie jar/browser SameSite semantics at all, so cookie mode was never an
 * option here — AsyncStorage is the plain-JS baseline every RN app can rely
 * on without extra native linking beyond itself.
 *
 * AsyncStorage is NOT encrypted at rest. Before shipping this to real users,
 * replace it with react-native-keychain (iOS Keychain / Android Keystore) —
 * noted in mobile/README.md's "Before shipping this anywhere real" section,
 * same honesty pattern as this project's other "MVP, not hardened" notes
 * (e.g. docs/KURT_WALLET.md).
 */
export const asyncStorageTokenStore: TokenStore = {
  async get() {
    return AsyncStorage.getItem(KEY);
  },
  async set(token) {
    if (token) {
      await AsyncStorage.setItem(KEY, token);
    } else {
      await AsyncStorage.removeItem(KEY);
    }
  },
};
