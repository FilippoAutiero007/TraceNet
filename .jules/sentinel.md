# Sentinel Security Journal 🛡️

## 2025-05-15 - Unanchored CORS Origin Regex
**Vulnerability:** The `CORSMiddleware` in FastAPI/Starlette was configured with an `allow_origin_regex` that lacked a `$` anchor.
**Learning:** `re.match` (used by Starlette) checks for a match at the beginning of the string. Without a `$` anchor, an attacker can bypass CORS by using a domain they control as a suffix to an allowed domain (e.g., `https://tracenet.vercel.app.attacker.com`).
**Prevention:** Always anchor security-critical regexes with `^` and `$` to ensure they match the entire string. In Starlette's `CORSMiddleware`, the `allow_origin_regex` is matched against the `Origin` header using `re.match`, so at least the `$` anchor is mandatory to prevent suffixing.
