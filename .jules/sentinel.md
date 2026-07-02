# Sentinel Security Journal

## 2025-05-15 - CORS Regex Subdomain Suffixing Bypass
**Vulnerability:** The CORS `allow_origin_regex` was not anchored at the end with `$`, allowing origins like `https://tracenet.vercel.app.attacker.com` to pass validation because `re.match` only checks for a match starting from the beginning of the string.
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for origin regex validation. Without an end anchor, any origin that starts with a valid pattern but ends with malicious content is accepted.
**Prevention:** Always anchor security-critical regexes with both `^` (implicit in `re.match` but good practice to be explicit if using `re.search`) and `$` to ensure a full-string match.
