"""NLP parser service with LLM + RAG guardrails for normalized JSON extraction."""

import json
import logging
import os
import re
from typing import Any

import httpx
from mistralai import Mistral
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.schemas import ParseIntent, ParseNetworkResponse
from app.services.rag_knowledge import NETWORK_PARSER_DOCUMENTS, retrieve_relevant_documents
from app.utils.cache import response_cache

logger = logging.getLogger(__name__)


class ParserServiceError(RuntimeError):
    """Raised when the parser backend fails for infrastructure or internal reasons."""

RAG_KNOWLEDGE_BASE = {
    "schema": {
        "base_network": "string CIDR",
        "routers": "integer >= 1",
        "switches": "integer >= 0",
        "pcs": "integer >= 1",
        "servers": "integer >= 0",
        "routing_protocol": "STATIC | RIP | OSPF | EIGRP",
        "subnets": [{"name": "string", "required_hosts": "integer >= 1"}],
    },
    "required_fields": ["base_network", "routers", "switches", "pcs", "routing_protocol"],
}

DEFAULT_FIELD_VALUES: dict[str, Any] = {
    "base_network": "192.168.1.0/24",
    "routers": 1,
    "switches": 1,
    "pcs": 4,
    "routing_protocol": "STATIC",
}

NETWORK_KEYWORDS = {
    "rete", "network", "router", "switch", "pc", "vlan", "subnet", "routing", "ospf", "rip", "eigrp", "cidr"
}
NETWORK_PATTERNS = [
    re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b"),
    re.compile(r"\b(?:nat|dhcp|acl|dmz|gateway|backbone|wan|lan)\b", re.IGNORECASE),
    re.compile(r"\b(?:static routing|router-on-a-stick|default route)\b", re.IGNORECASE),
]

class MistralResponseSchema(BaseModel):
    """Schema per validare la response di Mistral."""
    intent: ParseIntent
    missing: list[str] = Field(default_factory=list)
    json_payload: dict[str, Any] = Field(default_factory=dict, alias="json")

SYSTEM_PROMPT = """You are a strict network-request parser.
You must act as a parser/validator only. Never generate prose.
You MUST return exactly one valid JSON object with this schema:
{
  "intent": "not_network | incomplete | complete",
  "missing": ["field_name"],
  "json": {
    "base_network": "...",
    "routers": 1,
    "switches": 1,
    "pcs": 10,
    "routing_protocol": "STATIC",
    "subnets": [{"name": "LAN", "required_hosts": 10}]
  }
}
Rules:
- Use knowledge_base as guardrails.
- Merge explicit data from user_input with current_state. Keep previously collected values unless user clearly overrides them.
- If user request is unrelated to network configuration -> intent=not_network, missing=[], json={}
- If network-related but required fields are missing -> intent=incomplete and missing must list exact missing required fields.
- If complete -> intent=complete and json must contain normalized values.
- Normalize routing synonyms (e.g. statico/static routing -> STATIC).
- Extract explicit CIDR, device counts, routing protocol, servers, and subnet host requirements when present.
- If the user says to keep defaults / use default parameters, do not fabricate them here; leave fields missing so frontend can apply suggested defaults.
- Do NOT invent missing values.
- Do NOT calculate subnets, masks, or network math.
- Output JSON only. No markdown, no explanations.
"""


def _normalize_routing_protocol(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().upper()
    synonyms = {
        "STATIC": "STATIC",
        "STATIC ROUTING": "STATIC",
        "STATICO": "STATIC",
        "RIP": "RIP",
        "OSPF": "OSPF",
        "EIGRP": "EIGRP",
    }
    return synonyms.get(token)


def _extract_first_int(patterns: list[re.Pattern[str]], text: str) -> int | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            try:
                return int(match.group("count"))
            except (TypeError, ValueError):
                return None
    return None


def _extract_subnets(text: str) -> list[dict[str, Any]]:
    subnets: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    patterns = [
        re.compile(
            r"(?P<name>[A-Za-z][A-Za-z0-9_-]{1,31})\s*[:(]\s*(?P<hosts>\d+)\s*(?:host|hosts|utent[ei]|pc)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<name>[A-Za-z][A-Za-z0-9_-]{1,31})\s+con\s+(?P<hosts>\d+)\s+(?:host|utent[ei]|pc)\b",
            re.IGNORECASE,
        ),
    ]

    for pattern in patterns:
        for match in pattern.finditer(text):
            name = match.group("name").strip(" -_").upper()
            hosts = int(match.group("hosts"))
            key = (name, hosts)
            if hosts < 1 or key in seen:
                continue
            seen.add(key)
            subnets.append({"name": name, "required_hosts": hosts})

    return subnets


def _heuristic_parse(user_input: str) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    cidr_match = re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b", user_input)
    if cidr_match:
        extracted["base_network"] = cidr_match.group(0)

    lowered = user_input.lower()
    protocol_synonyms = {
        "static routing": "STATIC",
        "statico": "STATIC",
        "static": "STATIC",
        "ospf": "OSPF",
        "rip": "RIP",
        "eigrp": "EIGRP",
    }
    for token, normalized in protocol_synonyms.items():
        if token in lowered:
            extracted["routing_protocol"] = normalized
            break

    count_patterns = {
        "routers": [
            re.compile(r"\b(?P<count>\d+)\s*(?:router|routers)\b", re.IGNORECASE),
            re.compile(r"\brouter\s*x\s*(?P<count>\d+)\b", re.IGNORECASE),
        ],
        "switches": [
            re.compile(r"\b(?P<count>\d+)\s*(?:switch|switches)\b", re.IGNORECASE),
            re.compile(r"\bswitch\s*x\s*(?P<count>\d+)\b", re.IGNORECASE),
        ],
        "pcs": [
            re.compile(r"\b(?P<count>\d+)\s*(?:pc|pcs|computer|computers|client|clients|host|hosts)\b", re.IGNORECASE),
        ],
        "servers": [
            re.compile(r"\b(?P<count>\d+)\s*(?:server|servers)\b", re.IGNORECASE),
        ],
    }
    for key, patterns in count_patterns.items():
        value = _extract_first_int(patterns, user_input)
        if value is not None:
            extracted[key] = value

    if "subnets" not in extracted:
        subnet_matches = _extract_subnets(user_input)
        if subnet_matches:
            extracted["subnets"] = subnet_matches

    return extracted


def _merge_prefer_explicit(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in (overlay or {}).items():
        if value in (None, "", [], {}):
            continue
        merged[key] = value
    return merged


def _suggest_defaults(missing: list[str]) -> dict[str, Any]:
    return {field: DEFAULT_FIELD_VALUES[field] for field in missing if field in DEFAULT_FIELD_VALUES}


def _is_simple_single_network(data: dict[str, Any]) -> bool:
    routers = data.get("routers")
    servers = data.get("servers", 0)
    subnets = data.get("subnets") if isinstance(data.get("subnets"), list) else []
    topology = data.get("topology")
    vlans = data.get("vlans") if isinstance(data.get("vlans"), list) else []

    return (
        servers in (None, 0)
        and topology in (None, {})
        and len(vlans) == 0
        and len(subnets) <= 1
        and (routers is None or routers == 1)
    )


def _merge_with_state(parsed_json: dict[str, Any], current_state: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current_state or {})
    for key, value in (parsed_json or {}).items():
        if value in (None, "", [], {}):
            continue
        merged[key] = value

    if "routing_protocol" in merged:
        normalized = _normalize_routing_protocol(merged.get("routing_protocol"))
        if normalized:
            merged["routing_protocol"] = normalized

    return merged


def _validate_normalized_json(data: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    required = ["base_network", "routers", "switches", "pcs"]
    missing: list[str] = []

    normalized = dict(data)
    for field in required:
        if field not in normalized or normalized[field] in (None, "", []):
            missing.append(field)

    routers = normalized.get("routers")
    if routers is not None and (not isinstance(routers, int) or routers < 1):
        missing.append("routers")

    switches = normalized.get("switches")
    if switches is not None and (not isinstance(switches, int) or switches < 0):
        missing.append("switches")

    pcs = normalized.get("pcs")
    if pcs is not None and (not isinstance(pcs, int) or pcs < 1):
        missing.append("pcs")

    protocol = _normalize_routing_protocol(normalized.get("routing_protocol"))
    if protocol is not None:
        normalized["routing_protocol"] = protocol
    elif _is_simple_single_network(normalized):
        normalized["routing_protocol"] = "STATIC"
    else:
        missing.append("routing_protocol")

    if not isinstance(normalized.get("subnets"), list):
        normalized["subnets"] = []

    return sorted(set(missing)), normalized


def _is_network_related(user_input: str) -> bool:
    lowered = user_input.lower()
    keyword_hits = sum(1 for keyword in NETWORK_KEYWORDS if keyword in lowered)
    pattern_hits = sum(1 for pattern in NETWORK_PATTERNS if pattern.search(user_input))
    return keyword_hits >= 1 or pattern_hits >= 1


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def parse_network_request(
    user_input: str,
    current_state: dict[str, Any],
) -> ParseNetworkResponse:
    """Parse user text into strict normalized JSON intent contract."""
    if not _is_network_related(user_input):
        return ParseNetworkResponse(intent=ParseIntent.NOT_NETWORK, missing=[], json={})

    # Performance optimization: cache check
    cache_key = f"{user_input}:{json.dumps(current_state, sort_keys=True)}"
    cached = response_cache.get(cache_key)
    if cached:
        logger.info("Cache hit for network request")
        try:
            return ParseNetworkResponse.model_validate(cached)
        except Exception:
            logger.warning("Failed to validate cached response, falling back to LLM")
    heuristic_json = _heuristic_parse(user_input)
    heuristic_merged = _merge_with_state(heuristic_json, current_state)

    api_key = settings.mistral_api_key.get_secret_value() if settings.mistral_api_key else None
    if not api_key:
        logger.warning("Mistral API key not found in settings. NLP parsing is disabled.")
        merged = heuristic_merged
        missing, normalized = _validate_normalized_json(merged)

        if missing:
            return ParseNetworkResponse(
                intent=ParseIntent.INCOMPLETE,
                missing=missing,
                json=normalized,
                suggestedDefaults=_suggest_defaults(missing),
                error="NLP Service Unavailable: Mistral API Key missing on server.",
            )
        return ParseNetworkResponse(
            intent=ParseIntent.COMPLETE,
            missing=[],
            json=normalized,
            suggestedDefaults={},
            error="NLP Service Unavailable: Mistral API Key missing on server.",
        )

    client = Mistral(api_key=api_key)
    retrieved_docs = retrieve_relevant_documents(
        [user_input, json.dumps(current_state, ensure_ascii=False)],
        NETWORK_PARSER_DOCUMENTS,
        limit=3,
    )

    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_input": user_input,
                            "current_state": current_state,
                            "knowledge_base": RAG_KNOWLEDGE_BASE,
                            "retrieved_context": retrieved_docs,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        try:
            data_dict = json.loads(raw_content)
            # Validazione formale con Pydantic
            validated_data = MistralResponseSchema.model_validate(data_dict)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Invalid response format from Mistral: %s. Content: %s", exc, raw_content)
            raise ParserServiceError(f"AI returned invalid or malformed JSON: {exc}") from exc

        parsed_json = _merge_prefer_explicit(heuristic_json, validated_data.json_payload)
        merged = _merge_with_state(parsed_json, current_state)
        missing, normalized = _validate_normalized_json(merged)

        if validated_data.intent == ParseIntent.NOT_NETWORK:
            res = ParseNetworkResponse(intent=ParseIntent.NOT_NETWORK, missing=[], json={})
        elif missing:
            res = ParseNetworkResponse(
                intent=ParseIntent.INCOMPLETE,
                missing=missing,
                json=normalized,
                suggestedDefaults=_suggest_defaults(missing),
            )
        else:
            res = ParseNetworkResponse(intent=ParseIntent.COMPLETE, missing=[], json=normalized, suggestedDefaults={})

        # Cache the response
        response_cache.set(cache_key, res.model_dump())
        return res

    except Exception as exc:
        logger.error("Parser failure: %s", exc, exc_info=True)
        if isinstance(exc, ParserServiceError):
            raise
        raise ParserServiceError("Failed to parse network request.") from exc
