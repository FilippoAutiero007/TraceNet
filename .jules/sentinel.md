## 2026-06-25 - CORS Origin Regex Subdomain Bypass
**Vulnerability:** Starlette's CORSMiddleware uses `re.match` for origin validation. Without a trailing `$` anchor, an attacker could bypass CORS by using a domain like `tracenet.vercel.app.attacker.com`.
**Learning:** Always anchor regexes used for security validation, especially for CORS origins and path traversal checks.
**Prevention:** Use `$` to anchor the end of origin regexes.
