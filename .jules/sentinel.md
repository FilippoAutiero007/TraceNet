## 2025-05-14 - [Authorization Bypass via Spoofable Origin Header]
**Vulnerability:** The auth service was checking the `Origin` HTTP header as a fallback for the `azp` claim when validating Clerk tokens.
**Learning:** `Origin` headers are easily spoofed by non-browser clients (like `curl` or custom scripts), allowing an attacker to impersonate an authorized application.
**Prevention:** Always rely on signed claims (like `azp` in JWT) for authorization rather than trustable-looking HTTP headers.

## 2025-05-14 - [Memory Exhaustion DoS in File Analysis]
**Vulnerability:** Endpoints for `.pkt` file analysis were reading the entire upload into memory without a size limit.
**Learning:** `await file.read()` in FastAPI/Starlette without a limit parameter can lead to immediate RAM exhaustion if a large file is uploaded.
**Prevention:** Use `await file.read(limit + 1)` and verify `len(data) <= limit` for all file upload endpoints.
