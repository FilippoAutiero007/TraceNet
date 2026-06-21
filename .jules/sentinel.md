# Sentinel Security Journal

This journal records critical security learnings and vulnerability patterns discovered by Sentinel.

## 2025-05-15 - [Anchoring CORS Origin Regex]
**Vulnerability:** The CORS `allow_origin_regex` in `backend/app/main.py` was missing an end-of-string anchor (`$`).
**Learning:** Starlette's `CORSMiddleware` uses `re.match` for origin validation. Without `$`, an attacker can bypass the policy by suffixing a trusted domain (e.g., `https://tracenet.vercel.app.attacker.com`).
**Prevention:** Always anchor security-critical regexes with `^` and `$`. Since `re.match` already anchors at the start, ensuring the `$` anchor is present is vital for domain validation.
