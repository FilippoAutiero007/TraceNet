# Sentinel Security Journal

## 2025-05-15 - CORS Subdomain Suffixing Bypass
**Vulnerability:** The `origin_regex` in `backend/app/main.py` lacked the `$` anchor, allowing origins like `https://tracenet.vercel.app.attacker.com` to pass the `re.match` check used by Starlette's `CORSMiddleware`.
**Learning:** Starlette's `CORSMiddleware` (v0.38.6) returns a 400 error for preflight (OPTIONS) requests if the Origin is not allowed and `allow_credentials=True`, but for simple requests (GET), it simply omits the CORS headers. `re.match` only anchors to the beginning of the string, making `$` critical for domain validation.
**Prevention:** Always anchor security-critical regexes with `^` and `$`. In FastAPI/Starlette, explicitly test both preflight and simple requests with malicious suffixed origins.
