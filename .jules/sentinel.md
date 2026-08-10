## 2025-05-15 - CORS Origin Regex Suffix Bypass
**Vulnerability:** The `origin_regex` in `backend/app/main.py` was missing a `$` anchor, allowing attackers to bypass CORS by using domains like `https://tracenet.vercel.app.attacker.com`.
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for origin validation. Without anchoring the end of the string, any domain starting with the allowed pattern is accepted.
**Prevention:** Always anchor security-critical regexes with `$` to ensure an exact match and prevent subdomain suffixing or path-based bypasses.
