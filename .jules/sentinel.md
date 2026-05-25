## 2026-05-25 - Authentication and Configuration Hardening
**Vulnerability:** Use of spoofable 'Origin' header for authorized party validation and risk of secret exposure in logs.
**Learning:** Authentication was validating the 'Origin' header which can be easily manipulated. Switching to the JWT 'azp' claim provides a cryptographically signed alternative. Also, the transition to Pydantic 'SecretStr' prevents sensitive API keys from appearing in debug logs or model dumps.
**Prevention:** Always prefer signed claims (like 'azp') over request headers for identity validation. Use 'SecretStr' for all API keys and credentials in configuration models.

## 2026-05-25 - Memory DoS Protection in File Uploads
**Vulnerability:** Unbounded file reads in analysis endpoints leading to potential memory exhaustion.
**Learning:** FastAPI's 'await file.read()' loads the entire content into RAM. Enforcing a strict limit (e.g., 10MB) using 'await file.read(limit + 1)' is necessary to prevent Denial of Service attacks.
**Prevention:** Implement explicit size checks on all file upload endpoints before processing the data.

## 2026-05-25 - Testing Components with Settings Singletons
**Vulnerability:** Not a vulnerability, but a codebase-specific testing challenge.
**Learning:** When using a centralized 'settings' object (singleton) in Python, patching environment variables via 'monkeypatch.setenv' often fails to affect the already-initialized settings.
**Prevention:** Use 'monkeypatch.setattr("app.config.settings.field_name", value)' to directly override configuration values in tests.
