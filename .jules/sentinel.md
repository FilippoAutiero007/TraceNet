# Sentinel Journal

## 2026-07-01 - CORS Origin Regex Subdomain Suffixing Bypass
**Vulnerability:** Unanchored CORS origin regex allowed subdomain suffixing bypasses. An attacker could use a domain like `https://tracenet.vercel.app.attacker.com` to pass the CORS check because the regex only verified the prefix.
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for `allow_origin_regex`. In Python, `re.match` matches from the beginning of the string but does not require it to match until the end unless explicitly anchored.
**Prevention:** Always anchor security-sensitive regular expressions with `$` (and `^` if not using a tool that implies it like `re.match`) to ensure full-string matching.
