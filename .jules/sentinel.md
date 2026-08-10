# Sentinel Security Journal

## 2025-05-14 - CORS Origin Regex Bypass via Subdomain Suffixing
**Vulnerability:** Insecure CORS origin regex in `backend/app/main.py`. The regex `r"https://(?:tracenet|nettrace)(?:-git-[^.]+)?\.vercel\.app"` was not anchored at the end.
**Learning:** Starlette's `CORSMiddleware` uses `re.match` (which matches from the start of the string) for `allow_origin_regex` validation. Without a terminal anchor (`$`), an attacker can bypass the filter by registering a domain like `https://tracenet.vercel.app.attacker.com`, which matches the prefix.
**Prevention:** Always anchor security-critical regexes with `$` when using them for origin validation or similar filters.
