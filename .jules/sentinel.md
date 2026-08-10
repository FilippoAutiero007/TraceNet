## 2025-05-15 - CORS Origin Regex Suffix Bypass
**Vulnerability:** The CORS `allow_origin_regex` in `backend/app/main.py` lacked a termination anchor (`$`), allowing origins like `https://tracenet.vercel.app.attacker.com` to pass validation.
**Learning:** Starlette's `CORSMiddleware` uses `re.match()` for origin regexes. In Python, `re.match()` checks from the beginning of the string but does not implicitly anchor the end, unlike some other frameworks or regex engines that might default to full-string matching for security configurations.
**Prevention:** Always use the `$` anchor in security-critical regexes, especially for origin validation, to prevent subdomain suffixing attacks.

## 2025-05-15 - Insecure Trust in Origin Header for Auth
**Vulnerability:** The `_validate_authorized_party` function in `backend/app/services/auth.py` allowed authentication if the `Origin` header matched a configured authorized party, even if the JWT's `azp` claim was missing or invalid.
**Learning:** Request headers like `Origin` are easily spoofed by non-browser clients (e.g., via `curl` or Postman). Relying on them for authentication validation provides a false sense of security and creates a trivial bypass for the `azp` claim check.
**Prevention:** Strictly rely on signed claims within the JWT (like `azp`) for identity and authorized party verification. Headers should only be used for secondary checks or non-security purposes.
