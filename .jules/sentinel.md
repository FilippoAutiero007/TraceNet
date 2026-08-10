# Sentinel Journal - Security Learnings

## 2025-05-14 - Unanchored CORS Regex Bypass
**Vulnerability:** CORS origin regex in `backend/app/main.py` was not anchored with `$`.
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for regex validation. Without a terminal anchor, an attacker can bypass CORS by using a domain that starts with a valid origin but has a malicious suffix (e.g., `https://tracenet.vercel.app.attacker.com`).
**Prevention:** Always anchor security-critical regexes with `^` and `$`.

## 2025-05-14 - Insecure Origin Header Verification in JWT Auth
**Vulnerability:** Clerk authentication in `backend/app/services/auth.py` allowed authorization if the `Origin` header matched a configured party, even if the `azp` claim in the signed JWT did not.
**Learning:** The `Origin` header is not a reliable security boundary for non-browser clients (like `curl` or mobile apps) which can spoof it. Security decisions must rely on cryptographically signed claims (like `azp`).
**Prevention:** Strictly validate signed JWT claims and never fallback to unauthenticated HTTP headers for authorization decisions.
