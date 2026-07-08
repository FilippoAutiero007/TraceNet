## 2026-07-06 - CORS Origin Regex Anchoring
**Vulnerability:** The CORS `origin_regex` in `backend/app/main.py` was missing a terminal anchor (`$`), allowing attackers to bypass CORS by using a malicious domain that starts with a legitimate Vercel domain (e.g., `https://tracenet.vercel.app.attacker.com`).
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for origin validation, which matches from the start of the string but does not require it to match until the end unless explicitly anchored.
**Prevention:** Always anchor security-critical regexes with `^` and `$` (or just `$` if using `re.match`) to ensure exact matches.

## 2026-07-06 - Early File Size Validation for DoS Mitigation
**Vulnerability:** The `/analyze-pkt` and `/analyze-pkt-report` endpoints were reading the entire uploaded file into memory using `await file.read()` before any size checks, posing a memory-exhaustion Denial-of-Service (DoS) risk.
**Learning:** FastAPI/Starlette's `UploadFile` objects provide a `.size` attribute that contains the file size if provided by the client (or determined by the spooler), allowing for an immediate check before reading the file stream.
**Prevention:** Implement file size limits early in the request lifecycle using `file.size` to reject oversized payloads before they consume server memory.
