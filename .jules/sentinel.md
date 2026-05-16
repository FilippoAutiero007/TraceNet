## 2024-05-15 - [DoS Prevention via File Size Limit]
**Vulnerability:** The `/api/analyze-pkt` endpoint allowed unlimited file uploads into memory, leading to potential Denial of Service (DoS) through resource exhaustion.
**Learning:** FastAPI's `UploadFile.read()` without a size limit can consume all available RAM if an attacker uploads a massive file.
**Prevention:** Always use `await file.read(limit + 1)` and check if the returned data length exceeds the allowed `limit`.

## 2024-05-15 - [Insecure Authorization via Spoofable Headers]
**Vulnerability:** Authentication logic occasionally fell back to the `Origin` header for authorized party validation when the `azp` claim was missing.
**Learning:** The `Origin` header is easily spoofed by non-browser clients (e.g., curl, postman), making it unsuitable for security-critical decisions.
**Prevention:** Rely exclusively on verified JWT claims (like `azp`) for authorized party validation and ignore spoofable HTTP headers.

## 2024-05-15 - [Secret Leakage in Logs]
**Vulnerability:** Sensitive API keys were handled as plain strings and accessed directly via environment variables.
**Learning:** Plain strings are easily leaked in stack traces or logs. Pydantic's `SecretStr` provides better protection by obfuscating the value in string representations.
**Prevention:** Use `SecretStr` for all sensitive configuration fields and access them via `.get_secret_value()` from a centralized settings object.
