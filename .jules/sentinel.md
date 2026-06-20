## 2025-05-15 - [CORS Origin Suffix Bypass]
**Vulnerability:** The CORS `allow_origin_regex` was not anchored with `$`, allowing an attacker to bypass CORS from a domain like `tracenet.vercel.app.attacker.com`.
**Learning:** Starlette's `CORSMiddleware` uses `re.match()` which only checks the beginning of the string.
**Prevention:** Always anchor security-related regexes with `^` and `$`.

## 2025-05-15 - [SlowAPI Request Parameter Requirement]
**Vulnerability:** Application crash when applying rate limiting.
**Learning:** `slowapi`'s `@limiter.limit` decorator strictly requires a parameter named `request` in the route function. If other parameters are present, `request` should ideally be the first one to avoid confusion.
**Prevention:** Ensure `request: Request` is present and correctly positioned in all rate-limited routes.
