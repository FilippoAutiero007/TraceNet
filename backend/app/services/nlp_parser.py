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
        "routing_protocol": "STATIC | RIP | OSPF | EIGRP",
        "subnets": [{"name": "string", "required_hosts": "integer >= 1"}],
    },
    "required_fields": ["base_network", "routers", "switches", "pcs", "routing_protocol"],
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
- If user request is unrelated to network configuration -> intent=not_network, missing=[], json={}
- If network-related but required fields are missing -> intent=incomplete and missing must list exact missing required fields.
- If complete -> intent=complete and json must contain normalized values.
- Normalize routing synonyms (e.g. statico/static routing -> STATIC).
- DO NOT hallucinate missing values. If a value is missing, it must be listed in "missing".
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
    required = ["base_network", "routers", "switches", "pcs", "routing_protocol"]
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
    if protocol is None:
        missing.append("routing_protocol")
    else:
        normalized["routing_protocol"] = protocol

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
    use_defaults: bool = False
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

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        logger.warning("MISTRAL_API_KEY not found. NLP parsing is disabled.")
        merged = _merge_with_state({}, current_state)
        missing, normalized = _validate_normalized_json(merged)

        defaults_applied = False
        if use_defaults:
            if "routers" in missing:
                normalized["routers"] = 1
                missing.remove("routers")
                defaults_applied = True
            if "switches" in missing:
                normalized["switches"] = 1
                missing.remove("switches")
                defaults_applied = True
            if "pcs" in missing:
                normalized["pcs"] = 2
                missing.remove("pcs")
                defaults_applied = True

        if missing:
            return ParseNetworkResponse(
                intent=ParseIntent.INCOMPLETE,
                missing=missing,
                defaults_applied=defaults_applied,
                json=normalized,
                error="NLP Service Unavailable: Mistral API Key missing on server.",
            )
        return ParseNetworkResponse(
            intent=ParseIntent.COMPLETE,
            missing=[],
            defaults_applied=defaults_applied,
            json=normalized,
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

        parsed_json = validated_data.json_payload
        merged = _merge_with_state(parsed_json, current_state)
        missing, normalized = _validate_normalized_json(merged)

        defaults_applied = False
        if use_defaults:
            if "routers" in missing:
                normalized["routers"] = 1
                missing.remove("routers")
                defaults_applied = True
            if "switches" in missing:
                normalized["switches"] = 1
                missing.remove("switches")
                defaults_applied = True
            if "pcs" in missing:
                normalized["pcs"] = 2
                missing.remove("pcs")
                defaults_applied = True

        if validated_data.intent == ParseIntent.NOT_NETWORK:
            res = ParseNetworkResponse(intent=ParseIntent.NOT_NETWORK, missing=[], json={})
        elif missing:
            res = ParseNetworkResponse(intent=ParseIntent.INCOMPLETE, missing=missing, defaults_applied=defaults_applied, json=normalized)
        else:
            res = ParseNetworkResponse(intent=ParseIntent.COMPLETE, missing=[], defaults_applied=defaults_applied, json=normalized)

        # Cache the response
        response_cache.set(cache_key, res.model_dump())
        return res

    except Exception as exc:
        logger.error("Parser failure: %s", exc, exc_info=True)
        if isinstance(exc, ParserServiceError):
            raise
        raise ParserServiceError("Failed to parse network request.") from exc
