## 2025-05-15 - [Authorization Hardening]
**Vulnerability:** Insecure reliance on the spoofable 'Origin' header for client identity verification in the authentication service.
**Learning:** The 'Origin' header can be easily manipulated by an attacker or a malicious client. Relying on it for security-critical decisions (like authorized party validation) is insecure when a cryptographic alternative (like the 'azp' claim in a verified JWT) is available.
**Prevention:** Always prioritize claims from verified tokens (JWT/OIDC) over standard HTTP headers for identity and authorization checks. Use 'azp' for identifying the client application and 'sub' for the user.
