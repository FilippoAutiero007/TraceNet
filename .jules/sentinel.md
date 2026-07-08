## 2026-06-30 - [CORS Regex Suffix Bypass]
**Vulnerability:** Unanchored CORS `allow_origin_regex` in FastAPI/Starlette allowed origins like `https://tracenet.vercel.app.attacker.com` to pass as valid.
**Learning:** Starlette's `CORSMiddleware` uses `re.match()` which matches from the start but doesn't implicitly anchor the end of the string.
**Prevention:** Always anchor security-critical regular expressions with `$` to prevent suffix-based bypasses.

## 2026-06-30 - [Upload DoS Mitigation]
**Vulnerability:** Packet Tracer file analysis endpoints were reading full file contents into memory without pre-validation of size.
**Learning:** `UploadFile` in FastAPI provides a `.size` attribute (from Starlette) that allows checking the `Content-Length` before consuming the stream.
**Prevention:** Implement explicit file size limits on all `UploadFile` parameters to prevent memory exhaustion.
