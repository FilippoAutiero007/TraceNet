## 2026-06-18 - Authorization Bypass via Origin Spoofing
**Vulnerability:** The `_validate_authorized_party` function in `backend/app/services/auth.py` allowed authentication tokens to be validated if the `Origin` header matched a configured authorized party, even if the cryptographically signed `azp` claim in the JWT did not match or was absent.
**Learning:** Checking the `Origin` header for authorization is insecure because it can be easily spoofed by non-browser clients (e.g., `curl`, Postman) or scripts, bypassing the intended restricted access to specific frontends.
**Prevention:** Authorization logic must strictly rely on immutable, signed claims within the JWT (like `azp`) rather than mutable request headers like `Origin` or `Referer`.
