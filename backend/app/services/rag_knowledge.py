from __future__ import annotations

from typing import Any


NETWORK_PARSER_DOCUMENTS = [
    {
        "id": "schema-core",
        "tags": ["json", "schema", "routing", "subnets"],
        "content": (
            "The normalized network JSON must contain base_network in CIDR notation, routers >= 1, "
            "switches >= 0, pcs >= 1, routing_protocol in STATIC/RIP/OSPF/EIGRP, and optional subnets "
            "as a list of {name, required_hosts}."
        ),
    },
    {
        "id": "normalization",
        "tags": ["static", "ospf", "rip", "eigrp", "normalize"],
        "content": (
            "Normalize routing synonyms: static, static routing, statico => STATIC. Preserve RIP, OSPF, "
            "and EIGRP as uppercase tokens. Never invent values that are not explicitly present."
        ),
    },
    {
        "id": "safety",
        "tags": ["validation", "missing", "incomplete"],
        "content": (
            "If required fields are missing, return intent=incomplete with the exact missing field names. "
            "Do not calculate masks, subnets, gateways, or host counts beyond what the user requested."
        ),
    },
    {
        "id": "advanced-networking",
        "tags": ["vlan", "nat", "acl", "dhcp", "server"],
        "content": (
            "If the user mentions VLANs, NAT, ACLs, DHCP, servers, or segmented networks, preserve these "
            "as structured hints only when they are explicit. Prefer exact extraction over speculative design."
        ),
    },
]


PKT_REVIEW_DOCUMENTS = [
    {
        "id": "review-goal",
        "tags": ["pkt", "review", "summary", "exercise"],
        "content": (
            "The Pro packet review must produce a concise remediation-oriented summary. Separate what already "
            "works from what must be fixed. Prioritize concrete networking corrections over generic advice."
        ),
    },
    {
        "id": "review-alignment",
        "tags": ["exercise", "requirements", "alignment"],
        "content": (
            "If an exercise description is provided, compare the imported Packet Tracer file against those "
            "requirements. Mention missing elements, mismatched routing intent, addressing inconsistencies, "
            "and topology gaps relative to the exercise."
        ),
    },
    {
        "id": "review-positive-findings",
        "tags": ["positive", "good", "correct"],
        "content": (
            "Positive findings should be factual: examples include coherent addressing, valid links, expected "
            "gateway placement, visible routing configuration, or subnet segmentation that matches the request."
        ),
    },
    {
        "id": "review-fixes",
        "tags": ["errors", "warnings", "fixes"],
        "content": (
            "Fix items should be actionable bullets. Use analyzer issues, device names, interfaces, and "
            "suggestions to explain what to change next."
        ),
    },
]


def retrieve_relevant_documents(
    query_parts: list[str],
    documents: list[dict[str, Any]],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    tokens = {
        token.strip(".,:;()[]{}!?").lower()
        for part in query_parts
        for token in str(part or "").split()
        if token.strip()
    }
    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in documents:
        haystack = f"{doc.get('content', '')} {' '.join(doc.get('tags', []))}".lower()
        score = sum(1 for token in tokens if token and token in haystack)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [doc for _, doc in scored[:limit]]
    if selected:
        return selected
    return documents[:limit]
