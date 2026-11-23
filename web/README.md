# Kurt web app

A thin client over `kurt/saas`'s hosted API — see
[docs/SAAS_FOUNDATION.md](../docs/SAAS_FOUNDATION.md) for the backend
contract this talks to, and the approved plan this came from for the
Phase 2-4 roadmap (browser extension, desktop, mobile + App Store/Play/
Huawei AppGallery IAP).

This is a Phase 0+1 scaffold: signup/login (session-cookie auth, added to
`kurt/saas/app.py` alongside the existing Bearer-token flow) and a minimal
chat UI over `/v1/chat`. It is **not** deployed anywhere and has no build/CI
pipeline yet — see `docs/SAAS_FOUNDATION.md`'s "Required before selling
subscriptions" section for what's still missing before real users.

## Run it locally

1. Start the backend (see `docs/SAAS_FOUNDATION.md`'s smoke-test section for
   the full env var list):

   ```sh
   export KURT_SAAS_STATE_DIR=/tmp/kurt-saas-dev
   export KURT_SAAS_DEV_INSECURE_HTTP=1   # local-only
   export KURT_SAAS_WEB_ORIGIN=http://localhost:5173
   export KURT_SAAS_GROQ_KEY=...          # optional — without it, chat 503s
   python3 -m uvicorn kurt.saas.app:create_app --factory --host 127.0.0.1 --port 8099
   ```

2. In a second terminal:

   ```sh
   cd web
   npm install
   npm run dev
   ```

3. Open <http://localhost:5173>, sign up, and chat.

`VITE_KURT_API_URL` (default `http://localhost:8099`) points the client at
a different backend if needed — see `.env.local` (gitignored) or your shell.
