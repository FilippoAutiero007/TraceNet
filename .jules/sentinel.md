## 2025-05-15 - [API Key Exposure in Frontend]
**Vulnerability:** Mistral API key was exposed in frontend via `VITE_MISTRAL_API_KEY` and used in a client-side hook `useMistral.ts`.
**Learning:** Vite environment variables prefixed with `VITE_` are bundled into the client-side code and accessible to anyone. Even if a hook is unused, having the secret in `.env` or used in code exposes it.
**Prevention:** Always handle sensitive API keys on the backend. Use Pydantic `SecretStr` to prevent accidental exposure in logs.
