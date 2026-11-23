import KurtApp from '../../web/src/App';
import { createKurtClient } from '../../web/src/api-client/client';
import { localTokenStore } from './tokenStore';
import LocalBridge from './LocalBridge';
import '../../web/src/index.css';

// Bearer-token client, same reasoning as the browser extension (see
// tokenStore.ts): Tauri's webview origin can't use the web app's cookie.
const client = createKurtClient({
  baseUrl: import.meta.env.VITE_KURT_API_URL ?? 'http://localhost:8099',
  tokenStore: localTokenStore,
});

export default function App() {
  return (
    <>
      <KurtApp client={client} />
      <LocalBridge />
    </>
  );
}
