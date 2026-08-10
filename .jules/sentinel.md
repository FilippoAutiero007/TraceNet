## 2026-06-05 - [Auth Bypass] Origin header spoofing in Clerk validation
**Vulnerability:** The authentication logic in `backend/app/services/auth.py` allowed authorization if the `Origin` header matched a configured allowed party, even if the `azp` claim in the JWT did not match or was missing.
**Learning:** The `Origin` header is not a reliable security boundary for non-browser clients, as it can be easily spoofed (e.g., via curl or scripts). Trusting it for authorization allows bypasses.
**Prevention:** Always rely on cryptographically signed claims within the JWT (like `azp`) for client authorization. Never use unauthenticated HTTP headers for security decisions.

## 2026-06-05 - [Pydantic Validation] Nested schema serialization in Route responses
**Vulnerability:** Not a security vulnerability, but a reliability issue. `GenerateResponse` was too restrictive, causing serialization failures when returning nested models or dictionaries in tests.
**Learning:** When a route returns a mix of Pydantic models and raw dictionaries for the same field, the schema must use `Union[Model, Dict[str, Any]]` to pass validation.
**Prevention:** Use `Union` in response schemas for fields that can contain either structured models or raw data mappings.
