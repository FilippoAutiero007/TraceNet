# Sentinel Journal

## 2025-05-15 - Pydantic Forward-Reference Resolution in Complex Schemas
**Vulnerability:** Not a direct vulnerability, but an architectural risk where circular or forward-referencing models (like `GenerateResponse` using `NetworkConfig`) cause runtime `NameError` or validation failures if not ordered correctly.
**Learning:** In projects with complex, nested Pydantic models, defining high-level response models at the very end of the file ensures all dependencies are fully initialized. Using `from __future__ import annotations` is necessary but sometimes insufficient for complex Union types that Pydantic needs to evaluate at runtime.
**Prevention:** Order Pydantic models by dependency (bottom-up) and place top-level API response models at the end of the schema file.

## 2025-05-15 - Insecure 'Origin' Header Fallback in Authentication
**Vulnerability:** Authorization bypass. The `_validate_authorized_party` function allowed both `azp` (Authorized Party) from JWT claims AND the `Origin` HTTP header as valid indicators of the client's identity. Since the `Origin` header can be easily spoofed by non-browser clients (e.g., via `curl` or `requests`), this provided a trivial bypass of the client restriction.
**Learning:** Never trust client-controlled headers like `Origin` or `Referer` for security-critical identity verification. Only cryptographic claims inside the JWT (like `azp`) should be used to verify the authorized client.
**Prevention:** Strictly rely on JWT claims for identity verification. Remove all code paths that allow unverified HTTP headers to satisfy authorization checks.
