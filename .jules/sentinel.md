## 2025-05-15 - [Resource Exhaustion]
**Vulnerability:** The `/api/analyze-pkt` and `/api/analyze-pkt-report` endpoints lacked file size limits on uploads, making the server vulnerable to memory exhaustion (DoS) attacks.
**Learning:** FastAPI's `UploadFile` reads into memory or spool to disk, but `await file.read()` without arguments loads the entire content into RAM.
**Prevention:** Always use `await file.read(limit + 1)` and check the length of the result to enforce size limits before further processing.

## 2025-05-15 - [Configuration Inconsistency]
**Vulnerability:** Mixing `os.environ.get` with a centralized Pydantic `Settings` object led to inconsistent configuration handling and potential security bypasses if environment variables were not properly synced.
**Learning:** Centralizing all configurations (like `output_dir`) into a Pydantic `BaseSettings` object and using it consistently across the app improves security auditability and testing reliability.
**Prevention:** Access all configurations and secrets through the `settings` singleton from `app.config`.

## 2025-05-15 - [Auth: Spoofable Origin Header]
**Vulnerability:** The backend checked both the JWT 'azp' claim AND the 'Origin' header for authorized parties. The 'Origin' header is easily spoofed by non-browser clients (like `curl` or scripts).
**Learning:** In a cross-origin API where authentication is handled via cryptographically signed JWTs, the 'azp' (Authorized Party) claim is the source of truth. The 'Origin' header should be ignored for authorization purposes.
**Prevention:** Rely solely on 'azp' or other signed claims for identifying the calling application.
