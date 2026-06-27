## 2025-05-14 - Insecure CORS Origin Regex
**Vulnerability:** The `origin_regex` in `backend/app/main.py` lacked a `$` anchor (e.g., `r"https://(?:tracenet|nettrace)(?:-git-[^.]+)?\.vercel\.app"`), allowing attackers to bypass CORS via domains like `tracenet.vercel.app.attacker.com`.
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for `allow_origin_regex`, which only matches from the beginning of the string. Without a `$` anchor, any origin that *starts* with a valid pattern will be accepted.
**Prevention:** Always anchor security-critical regexes with `$` when using `re.match` or frameworks that use it for validation (like Starlette/FastAPI CORS middleware).
