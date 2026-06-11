# Sentinel Journal - TraceNet

## 2024-05-24 - Authorization Bypass via Spoofable Origin Header
**Vulnerability:** The authentication service allowed authorized party validation to succeed if either the JWT `azp` claim OR the request `Origin` header matched the allowlist.
**Learning:** Using the `Origin` header as a fallback for authorization is insecure because it is a client-side header that can be easily spoofed by non-browser clients (e.g., scripts, `curl`), allowing them to masquerade as the official frontend.
**Prevention:** Always rely on cryptographically signed claims within the JWT (like `azp`) for identity and authorized party verification. Never use spoofable HTTP headers for security-critical decisions.
