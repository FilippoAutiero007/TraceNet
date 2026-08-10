## 2024-05-22 - [Harden Authentication & Secret Management]
**Vulnerability:** Insecure 'Origin' header check and hardcoded secret access in services.
**Learning:** The 'Origin' header is easily spoofed by non-browser clients, making it unreliable for authorized party verification. Also, accessing 'os.environ' directly in services bypasses Pydantic's 'SecretStr' protection.
**Prevention:** Always rely on signed JWT claims like 'azp' for client identity. Centralize configuration in a Pydantic Settings object and use 'SecretStr' to prevent accidental leakage in logs.
>>>>>>> REPLACE
