## 2025-05-15 - [Testing] Centralized Settings and Mocking
**Vulnerability:** Inconsistent security configuration and secret handling.
**Learning:** Migrating from `os.environ` to a centralized Pydantic `Settings` class with `SecretStr` improves security but changes how tests must be written. Patching environment variables via `monkeypatch.setenv` no longer works for components that use the already-initialized `settings` singleton.
**Prevention:** When testing components that depend on `app.config.settings`, use `monkeypatch.setattr("app.config.settings.field_name", value)` to ensure the mock is correctly applied to the singleton instance.
