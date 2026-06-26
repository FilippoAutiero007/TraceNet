# Sentinel Security Journal

## 2026-06-26 - CORS Regex Subdomain Suffixing Bypass
**Vulnerability:** The CORS `allow_origin_regex` in `backend/app/main.py` was not anchored with `$`.
**Learning:** Starlette's `CORSMiddleware` uses `re.match()` for regex validation. Without an end-of-string anchor (`$`), a malicious origin like `https://tracenet.vercel.app.attacker.com` would successfully match a regex intended only for `https://tracenet.vercel.app`.
**Prevention:** Always anchor security-critical regular expressions with `^` and `$` to ensure exact matches and prevent prefix/suffix bypasses.
