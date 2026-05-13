## 2026-05-13 - [DoS] Missing File Size Limit on Uploads
**Vulnerability:** The `/api/analyze-pkt` endpoint lacked a file size limit, allowing potential memory-based Denial of Service (DoS) attacks by uploading extremely large `.pkt` files.
**Learning:** Even if documentation or memory suggests a limit exists, it must be explicitly enforced in the code using `await file.read(max_size + 1)` before processing.
**Prevention:** Always enforce `max_length` constraints on Pydantic models and explicit byte-size limits on all file upload streams.
