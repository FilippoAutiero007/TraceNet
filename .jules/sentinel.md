## 2025-05-15 - Multi-Layer Security Hardening

**Vulnerability:**
1. Potential secret leakage via logs/tracebacks of `mistral_api_key`.
2. Potential Denial of Service (DoS) through unbounded Packet Tracer (`.pkt`) file uploads.
3. Authorization bypass risk due to reliance on the spoofable `Origin` header instead of cryptographically signed JWT claims.
4. Schema-level validation failures causing service instability (existing test failures).

**Learning:**
1. Pydantic `SecretStr` is essential for fields that should not be accidentally serialized or logged.
2. Direct `os.environ` usage in distributed services bypasses the centralized validation and documentation provided by a `BaseSettings` object.
3. The `Origin` header is a browser-enforced security mechanism but is NOT a reliable source for server-side authorization checks against non-browser clients (e.g., scripts, curl).
4. Strict schema validation (Pydantic) in response models can break existing endpoints if internal models are not explicitly mapped or unionized in the response schema.

**Prevention:**
1. Use `SecretStr` for all API keys and credentials in the config.
2. Implement size limits on all file upload endpoints before processing data.
3. Use signed JWT claims (like `azp`) for service-to-service or app-to-service authorization.
4. Use `Union` types in Pydantic response models to handle both dicts and nested Pydantic models returned by services.
