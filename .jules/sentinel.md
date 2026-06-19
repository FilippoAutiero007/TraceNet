## 2025-05-15 - [CORS Origin Suffix Bypass]
**Vulnerability:** The `origin_regex` in `backend/app/main.py` was unanchored at the end, allowing domains like `https://tracenet.vercel.app.evil.com` to bypass CORS.
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for `allow_origin_regex`. Without a `$` anchor, it matches any origin that *starts* with the pattern.
**Prevention:** Always anchor security-critical regexes with `^` and `$`.

## 2025-05-15 - [Insecure Authentication Fallback to Origin Header]
**Vulnerability:** `_validate_authorized_party` in `backend/app/services/auth.py` fell back to checking the `Origin` header if the `azp` claim was missing or didn't match.
**Learning:** The `Origin` header is easily spoofed by non-browser clients (e.g., `curl`, scripts), allowing them to bypass authorized party restrictions.
**Prevention:** Rely strictly on cryptographically signed JWT claims (like `azp`) for identity verification and never trust client-provided headers for authorization decisions.
