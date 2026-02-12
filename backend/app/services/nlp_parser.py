"""NLP parser service with LLM + RAG guardrails for normalized JSON extraction."""

import json
import logging
import os
from typing import Any

import httpx
from mistralai import Mistral
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.models.schemas import ParseIntent, ParseNetworkResponse

logger = logging.getLogger(__name__)

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
    "limits": {
        "routers": ">= 1",
        "switches": ">= 0",
        "pcs": ">= 1",
        "subnet_required_hosts": ">= 1",
    },
    "allowed_values": {
        "routing_protocol": ["STATIC", "RIP", "OSPF", "EIGRP"],
        "routing_synonyms": {
            "static": "STATIC",
            "static routing": "STATIC",
            "statico": "STATIC",
            "rip": "RIP",
            "ospf": "OSPF",
            "eigrp": "EIGRP",
        },
    },
    "examples": {
        "valid": [
            "Rete 10.0.0.0/24 con 1 router, 2 switch, 30 pc, routing statico",
            "Network 192.168.10.0/24, routers 2, switches 4, pcs 120, OSPF",
        ],
        "invalid": [
            "Scrivimi una poesia",
            "Voglio una rete bella senza dettagli",
        ],
    },
}

NETWORK_KEYWORDS = {
    "rete", "network", "router", "switch", "pc", "vlan", "subnet", "routing", "ospf", "rip", "eigrp", "cidr"
}

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
    return any(keyword in lowered for keyword in NETWORK_KEYWORDS)


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException, Exception)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def parse_network_request(user_input: str, current_state: dict[str, Any]) -> ParseNetworkResponse:
    """Parse user text into strict normalized JSON intent contract."""
    if not _is_network_related(user_input):
        return ParseNetworkResponse(intent=ParseIntent.NOT_NETWORK, missing=[], json={})

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        merged = _merge_with_state({}, current_state)
        missing, normalized = _validate_normalized_json(merged)
        if missing:
            return ParseNetworkResponse(intent=ParseIntent.INCOMPLETE, missing=missing, json={})
        return ParseNetworkResponse(intent=ParseIntent.COMPLETE, missing=[], json=normalized)

    client = Mistral(api_key=api_key)

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
            raise ValueError(f"AI returned invalid or malformed JSON: {exc}")

        parsed_json = validated_data.json_payload
        merged = _merge_with_state(parsed_json, current_state)
        missing, normalized = _validate_normalized_json(merged)

        if validated_data.intent == ParseIntent.NOT_NETWORK:
            return ParseNetworkResponse(intent=ParseIntent.NOT_NETWORK, missing=[], json={})

        if missing:
            return ParseNetworkResponse(intent=ParseIntent.INCOMPLETE, missing=missing, json={})

        return ParseNetworkResponse(intent=ParseIntent.COMPLETE, missing=[], json=normalized)

    except Exception as exc:
        logger.error("Parser failure: %s", exc, exc_info=True)
        if isinstance(exc, ValueError):
            raise exc
        raise ValueError(f"Failed to parse network request: {str(exc)}")
