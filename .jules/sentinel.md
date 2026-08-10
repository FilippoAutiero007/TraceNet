## 2024-05-15 - [DoS Mitigation via File Size Limit]
**Vulnerability:** Resource exhaustion (DoS) due to unbounded file uploads on the `/api/analyze-pkt` endpoint.
**Learning:** Large `.pkt` files (which are actually compressed XML) can cause excessive memory consumption when read entirely into memory and then decrypted/parsed.
**Prevention:** Always enforce a strict `max_length` or use `await file.read(limit + 1)` and check the length before processing uploaded files.
