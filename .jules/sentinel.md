## 2025-05-15 - [CORS] Fixed origin regex vulnerability

**Vulnerability:** The CORS `origin_regex` in `backend/app/main.py` was missing the `$` anchor, allowing subdomain suffixing attacks (e.g., `https://tracenet.vercel.app.attacker.com`).
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for `allow_origin_regex` validation, which only checks the beginning of the string. Without a trailing anchor, any domain starting with a valid origin would be allowed.
**Prevention:** Always use anchors (`^` and `$`) in security-critical regexes to ensure an exact match.
