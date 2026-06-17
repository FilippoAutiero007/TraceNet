## 2025-05-22 - [XML External Entity (XXE) Protection]
**Vulnerability:** Use of standard `xml.etree.ElementTree.fromstring` which is vulnerable to XXE and DoS attacks when parsing untrusted XML data (like uploaded .pkt files).
**Learning:** Packet Tracer .pkt files are encrypted XML. Even if they appear binary, once decrypted they are standard XML. An attacker could craft a .pkt file that, when decrypted and parsed by the backend, triggers an XXE or Billion Laughs attack.
**Prevention:** Use `defusedxml` as a drop-in replacement for `ElementTree.fromstring` to securely parse XML data. Always use a dual-import pattern to keep `xml.etree.ElementTree` for creation (e.g., `SubElement`) while using `defusedxml` for parsing.
