## 2025-05-14 - [Enforce File Size Limits for Uploads]
**Vulnerability:** The `/api/analyze-pkt` endpoint lacked a file size limit on uploaded `.pkt` files, allowing an attacker to upload extremely large files and cause an Out-Of-Memory (OOM) Denial of Service (DoS).
**Learning:** FastAPI's `UploadFile` reads data into memory. Without an explicit limit via `file.read(limit + 1)`, the server is vulnerable to resource exhaustion.
**Prevention:** Always enforce a maximum file size limit for all file upload endpoints using `await file.read(limit + 1)` and checking the resulting length.
