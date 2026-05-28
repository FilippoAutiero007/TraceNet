## 2025-05-15 - [Authorization: AZP vs Origin]
**Vulnerability:** The authentication service was validating the 'Origin' header as an alternative to the 'azp' (Authorized Party) claim in JWTs.
**Learning:** The 'Origin' header is set by the browser but can be easily spoofed by non-browser clients (e.g., via curl or scripts), making it unreliable for identity verification. In contrast, the 'azp' claim is part of the cryptographically signed JWT payload provided by the OIDC provider (Clerk).
**Prevention:** Always rely on signed token claims (like 'azp' or 'aud') for client identity verification in APIs. Do not use spoofable HTTP headers for security-critical decisions.
