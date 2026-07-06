## 2026-05-29 - [XML External Entity (XXE) Prevention]
**Vulnerability:** Parsing untrusted Cisco Packet Tracer (.pkt) XML data with standard `xml.etree.ElementTree` is vulnerable to XXE and XML bomb attacks.
**Learning:** Packet Tracer files are encrypted/obfuscated but once decrypted they contain standard XML that can be manipulated by attackers.
**Prevention:** Always use `defusedxml` when parsing XML from external sources, especially when the content is derived from user uploads.
