import React from 'react';
import ReactDOM from 'react-dom/client';
import App from '../../../web/src/App';
import { createKurtClient } from '../../../web/src/api-client/client';
import { chromeTokenStore } from '../tokenStore';
import '../../../web/src/index.css';

// Bearer-token client (not the web app's default cookie client) — see
// web/src/api-client/client.ts's module docstring for why. Must match
// manifest.json's host_permissions, or requests will be blocked.
const client = createKurtClient({
  baseUrl: import.meta.env.VITE_KURT_API_URL ?? 'http://localhost:8099',
  tokenStore: chromeTokenStore,
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App client={client} />
  </React.StrictMode>,
);
