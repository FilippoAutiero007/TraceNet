# Sentinel Journal 🛡️

This journal tracks critical security learnings, vulnerability patterns, and security-related decisions for the TraceNet project.

## 2025-05-14 - Resource Exhaustion via Unbounded Inputs
**Vulnerability:** The `/api/analyze-pkt` endpoint and several Pydantic models lacked size/count limits, creating a risk of Denial of Service (DoS) through memory exhaustion.
**Learning:** Even if an application doesn't have obvious "heavy" processing, unbounded `await file.read()` or large integer inputs in network topology generation can lead to resource exhaustion.
**Prevention:** Always enforce maximum file sizes on uploads and use Pydantic's `max_length` and `le` constraints for user-provided data that impacts resource allocation.
