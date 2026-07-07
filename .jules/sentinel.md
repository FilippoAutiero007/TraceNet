## 2026-07-07 - [CORS Regex Anchor Bypass]
**Vulnerability:** The CORS origin regex was unanchored at the end (missing '$'), allowing attackers to bypass CORS via subdomain suffixing (e.g., tracenet.vercel.app.attacker.com).
**Learning:** Starlette's CORSMiddleware uses regex matching for origins. Without anchors, regexes can match unintended subdomains.
**Prevention:** Always anchor security-critical regexes with '^' and '$' to ensure exact matches.

## 2026-07-07 - [Pydantic Forward References and Union Types]
**Vulnerability:** Not a direct security vulnerability, but rigid Pydantic models caused 500 errors (Internal Server Error) during response validation, which can leak internal details.
**Learning:** Pydantic models referencing other models defined later in the file can cause runtime issues if not handled carefully. Using Union[Model, Dict[str, Any]] provides a safer fallback for response payloads.
**Prevention:** Define top-level response models at the end of the schema file and use Union types for flexible response validation to avoid 500 errors.
