# Gemini CLI through Kurt

Kurt's direct Gemini CLI adapter explicitly selects `gemini-3.5-flash-lite`.
This applies to CLI delegation, `/gemini`, and Gemini as the default CLI;
it does not change the chat API default or wallet-managed model routing.

An explicit `--model`/`-m` argument takes precedence. Set
`KURT_GEMINI_MODEL` in Kurt's environment or `~/.kurt/.env` to choose another
model on the next launch. Model availability and inference quota depend on
the Google account. A model appearing in Google's listing does not guarantee
inference access: on November 19, Google listed `gemini-2.5-flash` and
`gemini-2.5-flash-lite` but rejected generation for this account with 404,
while `gemini-3.8-flash` (and `3.7`/`3.6`/`3.5-flash`) timed out with 503
high demand. Google's recommended GA `gemini-3.5-flash-lite` (as well as
`gemini-3-flash-preview` and `gemini-3.1-flash-lite`) responded cleanly and
passed live verification on both Gemini CLI and Kurt's direct API router.

Google's 503 high-demand response is a provider availability failure, not proof
of a bad key. Gemini CLI can perform its own retries within Kurt's 120-second
process limit. Kurt does not automatically replay a failed task. Do not retry
tasks with side effects until their actual outcome has been checked.

Headless Gemini also requires workspace trust. Kurt does not automatically
trust real projects or disable tool approvals. Verification uses an explicitly
trusted synthetic temporary workspace only.
