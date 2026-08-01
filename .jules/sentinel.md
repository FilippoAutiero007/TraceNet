## 2025-05-15 - Unanchored CORS Regex Bypass in Starlette
**Vulnerability:** Starlette's `CORSMiddleware` (used by FastAPI) uses `re.match` for `allow_origin_regex`. An unanchored regex like `https://tracenet\.vercel\.app` successfully matches `https://tracenet.vercel.app.attacker.com`, allowing unauthorized origins.
**Learning:** `re.match` only checks the start of the string. Without a trailing `$`, the middleware is vulnerable to subdomain suffixing attacks.
**Prevention:** Always anchor security-critical regexes with `$` (and `^` for clarity) when used for origin validation.
