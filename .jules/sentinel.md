## 2025-05-22 - Authentication and Information Protection Hardening

**Vulnerability:** Authorization bypass via spoofed Origin header and potential secret leakage in logs.

**Learning:**
1. The Clerk authentication implementation was checking both the `azp` claim and the `Origin` header for authorization. While `azp` is a claim within a signed JWT, the `Origin` header is a client-provided HTTP header that can be easily spoofed by non-browser clients (e.g., via `curl` or Postman), leading to an authorization bypass for non-browser requests.
2. Sensitive API keys (Mistral) were stored as plain strings in Pydantic models, which could lead to accidental exposure if the settings object was logged or serialized.
3. Lack of file size limits on `.pkt` upload endpoints posed a memory exhaustion (DoS) risk.

**Prevention:**
1. Always rely on cryptographically verified claims (like `azp` in a JWT) rather than mutable HTTP headers for authorization logic.
2. Use Pydantic's `SecretStr` for all sensitive configuration fields to ensure they are masked during logging and serialization.
3. Implement explicit file size validation on all file upload endpoints before processing the content.
4. When testing singleton-like settings, use `monkeypatch.setattr` on the attribute itself rather than `monkeypatch.setenv` to ensure the already-initialized object is correctly patched.
