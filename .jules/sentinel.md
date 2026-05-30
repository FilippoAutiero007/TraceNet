## 2024-05-30 - [Hardened XML Parsing with defusedxml]
**Vulnerability:** Use of standard library `xml.etree.ElementTree` for parsing Cisco Packet Tracer XML files, which is vulnerable to XML External Entity (XXE) and Billion Laughs DoS attacks.
**Learning:** `defusedxml.ElementTree` is a hardened wrapper for parsing but does NOT implement the full `xml.etree.ElementTree` API. Specifically, it lacks `Element`, `SubElement`, and other factory functions used for XML generation.
**Prevention:** Use a dual-import pattern: `import xml.etree.ElementTree as ET` for XML generation and type hinting, and `from defusedxml import ElementTree as DET` for secure parsing via `DET.fromstring()` or `DET.parse()`.
