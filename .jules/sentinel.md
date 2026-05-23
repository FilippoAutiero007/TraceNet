## 2025-05-15 - [API Key Hardening]
**Vulnerability:** API keys were accessed directly via os.environ and stored as plain strings in the config object, risking exposure in logs or accidental leaks.
**Learning:** Using Pydantic SecretStr and a centralized settings object ensures sensitive data is masked and validated during application startup.
**Prevention:** Always use SecretStr for sensitive credentials and avoid direct os.environ calls in business logic.
