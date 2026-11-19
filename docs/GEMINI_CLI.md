# Gemini CLI through Kurt

Kurt's direct Gemini CLI adapter explicitly selects `gemini-3.8-flash`.
This applies to CLI delegation, `/gemini`, and Gemini as the default CLI;
it does not change the chat API default or wallet-managed model routing.

An explicit `--model`/`-m` argument takes precedence. Set
`KURT_GEMINI_MODEL` in Kurt's environment or `~/.kurt/.env` to choose another
model on the next launch. Model availability and inference quota depend on
the Google account. A model appearing in Google's listing does not guarantee
inference access: on November 19, Google listed `gemini-2.5-flash` but rejected
generation for this account with a 404 and recommended `gemini-3.8-flash`.

Google's 503 high-demand response is a provider availability failure, not proof
of a bad key. Gemini CLI can perform its own retries within Kurt's 120-second
process limit. Kurt does not automatically replay a failed task. Do not retry
tasks with side effects until their actual outcome has been checked.

Headless Gemini also requires workspace trust. Kurt does not automatically
trust real projects or disable tool approvals. Verification uses an explicitly
trusted synthetic temporary workspace only.
