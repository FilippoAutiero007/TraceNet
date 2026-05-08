
## 2024-05-22 - LLM Response Caching
**Learning:** Repetitive NLP parsing of network requests is a major latency source and cost driver. Structured conversation states are often repeated or only slightly modified.
**Action:** Always implement a lightweight in-memory cache for LLM parsing results keyed by the combination of user input and current state. This reduces P99 latency significantly for follow-up questions.
