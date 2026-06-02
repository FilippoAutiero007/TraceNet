## 2025-05-15 - [Denial of Service via Unlimited File Uploads]
**Vulnerability:** Endpoints receiving `UploadFile` (FastAPI) were reading the entire file content into memory using `await file.read()` without any size constraints.
**Learning:** `UploadFile.read()` without arguments reads the whole file. If the file is large, it can lead to memory exhaustion (DoS).
**Prevention:** Always enforce a maximum file size by reading a limited number of bytes (`await file.read(limit + 1)`) and checking if the result exceeds the limit before further processing.

## 2025-05-15 - [Sensitive Data Exposure in Logs]
**Vulnerability:** API keys (Mistral) were stored as plain strings in Pydantic `BaseSettings`.
**Learning:** Plain strings are easily leaked if the settings object or its parent is logged or serialized.
**Prevention:** Use Pydantic's `SecretStr` for all sensitive credentials and access them explicitly with `.get_secret_value()`.
