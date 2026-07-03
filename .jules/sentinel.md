## 2024-05-15 - [CORS Subdomain Suffixing Bypass]
**Vulnerability:** The CORS `origin_regex` was unanchored at the end, allowing attackers to bypass the policy by using a malicious domain that suffixes a legitimate origin (e.g., `https://tracenet.vercel.app.attacker.com`).
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for `allow_origin_regex`. Since `re.match` only checks the beginning of the string, an unanchored regex is susceptible to suffix-based bypasses.
**Prevention:** Always anchor security-critical regexes with `$` (and `^` if not using `re.match`) to ensure the entire string is validated against the intended pattern.
