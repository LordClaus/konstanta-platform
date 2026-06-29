# AI Assistant — design notes

The candidate-facing chat assistant answers questions about vacancies, the
application process, housing, pay and documents. This note documents the
**provider abstraction**, the **prompt design**, and the **OpenAI integration**
(error handling, retries, cost/latency controls). Code lives in
`backend/app/services/ai/`.

## 1. Provider abstraction (Strategy + Factory)

```
routers/ai.py  →  services/ai/service.py  →  AIProvider (base.py)
                                              ├── OpenAIProvider   (openai_provider.py)
                                              └── GeminiProvider   (gemini_provider.py)
                          get_provider()  ←  factory.py  (config-driven, with fallback)
```

- `AIProvider` is a tiny interface: `available` + `async complete(system, messages)`.
- The router and service depend on the **interface**, never on a vendor —
  swapping OpenAI ↔ Gemini (or adding Anthropic later) is one new class plus one
  line in the factory registry. (Open/Closed + Dependency-Inversion in practice.)
- `factory.get_provider()` returns the configured vendor, falls back to any other
  vendor that has a key, and returns `None` when nothing is configured — in which
  case the endpoint answers `503` and the widget hides itself.

## 2. Prompt design

The prompt is assembled in `service.build_system_prompt()` from three parts:

1. **Role + policy (per language).** Localized system prompts (UA / CZ / EN) set
   the persona ("friendly recruitment-agency assistant"), the scope (which job
   types, the application flow, that the service is free for candidates), and the
   tone ("concise, answer in the user's language").
2. **Grounding.** The *current* vacancy list is injected into the prompt as a
   compact bullet block (`_jobs_block`). The model answers from this live context
   rather than from training data.
3. **Anti-hallucination guardrail.** The prompt explicitly forbids inventing
   vacancies that are not in the list and tells the model to defer to "apply on
   the site / contact a manager" when unsure.

Other deliberate choices:

- **Language mirroring** — one instruction ("answer in the user's language")
  instead of translating the whole prompt per request.
- **Context comes from the client**, so the chat endpoint never touches the
  database — see `routers/ai.py`.
- **Window + length caps** — only the last 12 messages are sent, each capped at
  2000 chars, and the vacancy list is capped at 40 — bounding token cost and
  latency regardless of what the client sends.

## 3. OpenAI integration (`openai_provider.py`)

Talks to `POST /v1/chat/completions` directly over `aiohttp` (no SDK) to keep the
dependency surface and cold-start small.

- **Configurable generation params** — `OPENAI_MODEL`, `OPENAI_MAX_TOKENS`,
  `OPENAI_TEMPERATURE`, `OPENAI_TIMEOUT_SECONDS` come from `Settings`, so the
  model/budget/latency can be tuned per environment without a code change.
- **Bounded retry** — one retry on a *transient* failure (HTTP 429 / 5xx, or a
  timeout) with a short backoff. A 4xx (e.g. malformed request, bad key) is
  treated as permanent and **not** retried. The retry count is capped so a
  failing upstream can't pile up slow requests on the event loop.
- **Testable HTTP seam** — the single network attempt lives in `_post_once()`;
  `complete()` only orchestrates retries. Tests replay `(status, json)` sequences
  through that seam to assert the retry policy without touching the network
  (`tests/unit/test_ai.py`).
- **Error mapping** — `AIProviderError("timeout")` → `504`, other upstream
  failures → `502`, no provider configured → `503`. On an empty/garbled body the
  service substitutes a localized fallback message instead of erroring.

## 4. Where to look

| Concern | File |
|---|---|
| Interface (Strategy) | `services/ai/base.py` |
| Vendor selection (Factory + fallback) | `services/ai/factory.py` |
| Prompt assembly + error→HTTP mapping | `services/ai/service.py` |
| OpenAI HTTP, params, retry | `services/ai/openai_provider.py` |
| Endpoint (thin, rate-limited) | `routers/ai.py` |
| Tests (prompt, factory, payload, retry) | `tests/unit/test_ai.py` |
