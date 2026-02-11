"""NLP parser service with LLM + RAG guardrails for normalized JSON extraction."""

import json
import logging
import os
import time
from hashlib import sha256
from threading import Lock
from typing import Any

import httpx
from mistralai import Mistral
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.models.schemas import ParseIntent, ParseNetworkResponse

logger = logging.getLogger(__name__)

_PARSE_CACHE_TTL_SECONDS = 300
_PARSE_CACHE_MAX_ENTRIES = 256
_PARSE_CACHE: dict[str, tuple[float, ParseNetworkResponse]] = {}
_PARSE_CACHE_LOCK = Lock()

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

MAX_USER_INPUT_CHARS = 4000

NETWORK_KEYWORDS = {
    "rete", "network", "router", "switch", "pc", "vlan", "subnet", "routing", "ospf", "rip", "eigrp", "cidr"
}

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




def _build_cache_key(user_input: str, current_state: dict[str, Any]) -> str:
    payload = json.dumps({"user_input": user_input, "current_state": current_state}, sort_keys=True, ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _get_cached_response(cache_key: str) -> ParseNetworkResponse | None:
    now = time.time()
    with _PARSE_CACHE_LOCK:
        record = _PARSE_CACHE.get(cache_key)
        if not record:
            return None
        expires_at, cached = record
        if now > expires_at:
            _PARSE_CACHE.pop(cache_key, None)
            return None
        return cached.model_copy(deep=True)


def _set_cached_response(cache_key: str, response: ParseNetworkResponse):
    with _PARSE_CACHE_LOCK:
        if len(_PARSE_CACHE) >= _PARSE_CACHE_MAX_ENTRIES:
            oldest_key = next(iter(_PARSE_CACHE))
            _PARSE_CACHE.pop(oldest_key, None)
        _PARSE_CACHE[cache_key] = (time.time() + _PARSE_CACHE_TTL_SECONDS, response.model_copy(deep=True))


def get_mistral_client(api_key: str) -> Mistral:
    """Factory extracted for dependency injection and testing."""
    return Mistral(api_key=api_key)


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException, Exception)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def parse_network_request(
    user_input: str,
    current_state: dict[str, Any],
    mistral_client: Mistral | None = None,
) -> ParseNetworkResponse:
    """Parse user text into strict normalized JSON intent contract."""
    user_input = (user_input or '').strip()
    if len(user_input) > MAX_USER_INPUT_CHARS:
        return ParseNetworkResponse(
            intent=ParseIntent.INCOMPLETE,
            missing=["user_input"],
            json_payload={"error": f"Input too long (max {MAX_USER_INPUT_CHARS} chars)"},
        )

    if not _is_network_related(user_input):
        return ParseNetworkResponse(intent=ParseIntent.NOT_NETWORK, missing=[], json_payload={})

    cache_key = _build_cache_key(user_input, current_state)
    cached_response = _get_cached_response(cache_key)
    if cached_response is not None:
        return cached_response

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        merged = _merge_with_state({}, current_state)
        missing, normalized = _validate_normalized_json(merged)
        if missing:
            response = ParseNetworkResponse(intent=ParseIntent.INCOMPLETE, missing=missing, json_payload={})
            _set_cached_response(cache_key, response)
            return response
        response = ParseNetworkResponse(intent=ParseIntent.COMPLETE, missing=[], json_payload=normalized)
        _set_cached_response(cache_key, response)
        return response

    client = mistral_client or get_mistral_client(api_key)

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

        data = json.loads(response.choices[0].message.content)
        parsed_json = data.get("json", {}) if isinstance(data, dict) else {}

        merged = _merge_with_state(parsed_json, current_state)
        missing, normalized = _validate_normalized_json(merged)

        if data.get("intent") == ParseIntent.NOT_NETWORK.value:
            response = ParseNetworkResponse(intent=ParseIntent.NOT_NETWORK, missing=[], json_payload={})
            _set_cached_response(cache_key, response)
            return response

        if missing:
            response = ParseNetworkResponse(intent=ParseIntent.INCOMPLETE, missing=missing, json_payload={})
            _set_cached_response(cache_key, response)
            return response

        response = ParseNetworkResponse(intent=ParseIntent.COMPLETE, missing=[], json_payload=normalized)
        _set_cached_response(cache_key, response)
        return response

    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON from parser model: %s", exc, exc_info=True)
        response = ParseNetworkResponse(
            intent=ParseIntent.INCOMPLETE,
            missing=["base_network", "routers", "switches", "pcs", "routing_protocol"],
            json_payload={
                "error": "NLP service returned invalid JSON",
                "fallback_message": "Please provide complete parameters manually",
            },
        )
        _set_cached_response(cache_key, response)
        return response
    except Exception as exc:
        logger.error("Parser failure: %s", exc, exc_info=True)
        response = ParseNetworkResponse(
            intent=ParseIntent.INCOMPLETE,
            missing=["base_network", "routers", "switches", "pcs", "routing_protocol"],
            json_payload={
                "error": "NLP service temporarily unavailable",
                "fallback_message": "Please provide complete parameters manually",
            },
        )
        _set_cached_response(cache_key, response)
        return response
