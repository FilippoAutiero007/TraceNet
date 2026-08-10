## 2025-06-28 - CORS Regex Bypass via Subdomain Suffixing
**Vulnerability:** The `origin_regex` in `backend/app/main.py` was missing the `$` anchor, allowing an attacker to bypass CORS by hosting a malicious site on a domain like `tracenet.vercel.app.attacker.com`.
**Learning:** Starlette's `CORSMiddleware` uses `re.match()` to validate origins against `allow_origin_regex`. In Python, `re.match()` matches from the start of the string, but if the regex is not explicitly anchored at the end with `$`, it will match any string that *starts* with a valid pattern, even if it has a malicious suffix.
**Prevention:** Always use the `$` anchor in CORS origin regexes to ensure an exact match of the domain. Additionally, verify the regex against "suffix-style" bypass attempts in unit tests.
