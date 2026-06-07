## 2025-05-15 - [File Size Limit for DoS Mitigation]
**Vulnerability:** Unconstrained file uploads to memory-buffered endpoints (`analyze_pkt_file`, `analyze_pkt_file_report`) allowed for potential memory exhaustion (DoS) attacks.
**Learning:** FastAPI's `UploadFile` reads the entire content into memory when `await file.read()` is called without explicit size checks, which can be exploited.
**Prevention:** Always validate `file.size` or process the file in chunks before reading the full payload into memory.
