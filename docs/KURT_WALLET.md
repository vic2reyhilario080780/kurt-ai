# Kurt Wallet — USD, actual provider cost, zero markup

Implemented locally for personal use. **Payment integration is prepared, not live.**
No merchant account, real purchase, provider top-up or deployment was performed.
Wallet routing is opt-in; existing personal BYOK behavior remains until connected.

## What one balance means

A single USD ledger authorizes requests through a gateway holding the provider
keys. Native Kurt model calls, generation and API-mode CLI sessions use that same
account. The user/client carries a Kurt device token; external CLIs receive
short-lived provider-scoped Kurt tokens, not the real provider keys or owner token.

Wallet credit is **not** an automatic transfer into fal.ai, DeepSeek or OpenRouter.
The operator still funds prepaid providers or supplies working billed API accounts.
A provider's insufficient-balance error cannot be fixed by creating a ledger credit.
Future Stripe receipts go to the operator's Stripe account; this integration does
not buy upstream credits or move funds to those providers.

The currency is USD only. Markup is fixed at **0%** and nonzero configuration is
rejected. There is no FX spread, per-call surcharge or inferred token-price debit.
Processor fees, taxes and provider credit-purchase fees are not added to usage
charges by this implementation. The owner absorbs any funding/processor difference.

## Balance, reservations and costs

- `balance_usd`: credited funds minus confirmed usage/adjustments.
- `reserved_usd`: in-flight or unverified requests' holds; these are **not charges**.
- `available_usd`: balance minus holds. Insufficient available balance blocks new
  paid requests **before** contacting the provider.
- `settled`: financial cost recorded, not proof the AI completed the user's task.
  Media still needs its independent file/render verification.

Money is integer pico-USD (1 USD = 10^12 units), with strict decimal parsing rather
than floating-point balances or per-request rounding fees. SQLite transactions
serialize credit, reservation and settlement. Duplicate requests and payment
events cannot create an additional charge/credit. Ledger entries are append-only.

Configured holds are conservative reservations, not a guaranteed upstream price
or a hard vendor spending cap. The personal template holds $1 per text request
and $25 per fal/Replicate generation; edit `reserve_usd` in the private config for
your actual workload. A confirmed provider charge can exceed a hold. The real
amount is recorded, including debt, and further spending is blocked until funded.
A crashed/disconnected/ambiguous request keeps its hold pending; it is never
silently assumed free or automatically replayed.

### Actual-cost sources

- OpenRouter: `usage.cost`, including legitimate zero-cost responses, or the
  generation receipt on reconciliation. [Official usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting).
- fal.ai: the matching request/endpoint's billed event, using its precision-safe
  nano-USD amount after discounts. Billing access requires the corresponding
  key permissions. Delayed/inaccessible events stay pending.
  [Official billing events](https://fal.ai/docs/platform-apis/v1/models/billing-events).
- Other providers: token/usage metadata and request IDs are recorded, but **no
  dollar amount is invented**. They remain pending until the local operator
  reconciles an actual provider bill. Replicate job/poll ownership is enforced.
  Published token-rate estimates cannot be enabled as actual-cost settlement.

Thus automatic cost finalization is not claimed for every provider. All supported
requests share the wallet, but some require manual invoice reconciliation.
Unknown costs remain reserved rather than disguised as exact bills.

## Provider and CLI coverage

Native routes: OpenRouter, OpenAI, Mistral, DeepSeek, Groq, Anthropic, Google,
fal.ai and Replicate. This includes image/video dispatch and Groq multipart
transcription. Optional cloud Anthropic vision is routed through the wallet;
its existing cloud-vision consent setting is still required. Local Ollama remains
independent and free of provider charges.

API-mode CLI routes:

| CLI | Gateway provider |
| --- | --- |
| Codex | OpenAI Responses |
| Claude Code | Anthropic Messages |
| Gemini CLI | Google native API |
| OpenClaw | Groq (the existing managed-model profile) |
| Vibe | Mistral |
| DeepSeek Agent / DeepSeek Terminal CLI | DeepSeek |
| GitHub Copilot CLI (BYOK) | OpenRouter; personal GitHub billing is separate |

Copilot uses an isolated home and the wallet's OpenRouter provider profile.
Its `COPILOT_OFFLINE=true` setting disables GitHub traffic, while model requests
still go over the network through the gateway. See [Copilot setup](COPILOT_CLI.md).

Standalone CLI calls outside Kurt and subscription/OAuth usage are not converted
into wallet credits. Wallet-mode wrappers isolate login/config state so they do
not silently use a separate personal subscription. Existing Gemini folder-trust
decisions are preserved without adding trust to a real workspace. Existing tool
permissions and Codex filesystem/network policy remain enforced.

The current gateway meters AI inference/generation protocols, **not every vendor
connector/tool API**. Unmetered provider-hosted search/connectors are disabled in
wallet CLI sessions; they do not silently bill another account. Native Kurt web
search skips unmetered Brave/Serper keys and uses its public key-free fallbacks.
Use `/cli use auto` for native Kurt search when a CLI's hosted search is unavailable.
Kurt's older `cloud ask` path is blocked in wallet mode to avoid an unmetered
legacy gateway; native wallet-routed chat is the supported path.

## Personal setup (when you choose to activate)

The commands below create new state with **zero** funds; they do not create a
merchant account or a completed payment. Run them yourself after reviewing the
configuration. This feature was not switched on automatically in your account.

```sh
kurt wallet init --state-dir "$HOME/.kurt-wallet"
# Terminal 1: gateway reads your existing setup keys inside the server only.
kurt wallet serve --state-dir "$HOME/.kurt-wallet" --personal
# Terminal 2: verify gateway, save private token-file reference, enable routing.
kurt wallet connect http://127.0.0.1:8098 --token-file "$HOME/.kurt-wallet/owner.kurt-token"
kurt wallet status
```

The welcome banner shows `Kurt Wallet · USD · 0% markup` when enabled. Inside chat:
`/wallet status`, `/wallet history`, `/wallet catalog`, `/wallet topup 10`, and
`/wallet reconcile REQUEST_UUID`. `kurt wallet ...` provides the same functions.
The top-up command returns a Checkout URL only when Stripe is configured; a
redirect or client message never credits the balance.

For personal bookkeeping/testing after funding the actual provider accounts,
local operator commands are explicitly separate from purchases:

```sh
kurt wallet credit 10 --state-dir "$HOME/.kurt-wallet" --reference personal-funding-001 --reason "Manual personal allocation; not a card payment"
kurt wallet settle REQUEST_UUID 0.002 --state-dir "$HOME/.kurt-wallet" --evidence provider-invoice-item-001
kurt wallet correct REQUEST_UUID 0.0018 --state-dir "$HOME/.kurt-wallet" --evidence provider-corrected-invoice-item-001
```

`settle` uses an actual bill, never an estimate. `correct` appends the difference
and retains the original ledger entry. Manual credit output says
`verified_payment: false`. There are no public credit, settlement or correction
HTTP endpoints. Use `kurt wallet off` to return to direct personal BYOK routing.
Environment-managed mode must be unset explicitly instead of silently overridden.

State/token files are private (directory 0700, database/token 0600). Do not commit
them. Only token hashes, usage counters, request IDs, money and audit references
are persisted—no prompts, generated media, responses or upstream keys. Device
provisioning uses expiring/revocable existing Kurt grants; money entries do not
expire when a token expires. Provider-key rotation requires restarting this
personal gateway. Keep this server on one private host/SQLite database.

## Prepared Stripe integration

Server settings are in `deploy/saas/wallet.env.example`; actual secrets belong in
a private environment/secret manager, not the repo. Set a real `payment_return_url`
in private `wallet-config.json`, configure USD Checkout, and deliver events to
`POST /wallet/payments/stripe`. Remote clients require HTTPS. The local HTTP
exception is for a loopback personal server only.

The handler verifies the HMAC against the original raw body and a recent timestamp,
then matches the paid Checkout session to its server-created order, USD amount,
mode, payment intent and test/live environment. Event idempotency uses canonical
business content; harmless delivery-metadata changes cannot double-credit.
Asynchronous payments wait for confirmed payment. Partial refunds and disputes
adjust the original credit idempotently; an already-spent refund can create debt
and freeze new requests. No card data is collected or stored by Kurt.
[Stripe signature and retry guidance](https://docs.stripe.com/events/manage-webhook-endpoints).

No real Stripe account/key was supplied, so an actual test-mode or live card
payment has **not** been verified. The integration is ready for that step when
you have a processor account; it is not represented as a completed payment setup.

## Verification

The final isolated project suite passed **475 tests**.
`tests/test_wallet_*.py` exercise precision, zero markup, concurrency/overspending,
scoped credentials, tenant isolation, duplicate requests, pending outcomes, exact
reported zero/nonzero cost, fal billing permissions/delay, Replicate ownership,
verified payments/refunds/disputes, corrections, private token files and SDK routing.

`PYTHONPATH=. python3 tools/verify_wallet.py --output /tmp/wallet-report.json`
runs a real local HTTP wallet service and the installed CLI executables against
mock upstream APIs. Nine native provider routes and all seven CLI adapters passed
that local protocol test with synthetic credits. This proves routing/authentication
compatibility, not real provider inference, paid renders or merchant settlement.
