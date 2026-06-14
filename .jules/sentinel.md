# Sentinel Security Journal 🛡️

This journal records CRITICAL security learnings, vulnerability patterns, and architectural security gaps discovered in the TraceNet codebase.

---

## 2025-05-15 - Authorization Bypass via Origin Header Spoofing

**Vulnerability:** The authentication middleware was checking both the `azp` (Authorized Party) claim in the JWT and the `Origin` header from the request. Since the `Origin` header can be easily spoofed by non-browser clients (e.g., via `curl` or custom scripts), an attacker could bypass the `azp` validation by providing a valid session token (even if intended for a different client) and spoofing the `Origin` of a trusted application.

**Learning:** Trusting client-provided headers for authorization decisions is a common pitfall. The JWT's `azp` claim is cryptographically signed and thus trustworthy, whereas the `Origin` header is only reliable for CORS enforcement by browsers.

**Prevention:** Always rely on signed claims within the token for authorization. Use the `Origin` header only for its intended purpose (CORS) and ensure CORS policies are strictly configured.
