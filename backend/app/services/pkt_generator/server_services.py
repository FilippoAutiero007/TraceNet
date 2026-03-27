from __future__ import annotations

from typing import Any


def normalize_services(values: Any) -> set[str]:
    """
    Normalize server service names to a lowercase set.
    Accepted inputs: list/tuple/set. Other types return an empty set.
    """
    if not isinstance(values, (list, tuple, set)):
        return set()
    out: set[str] = set()
    for item in values:
        service = str(item or "").strip().lower()
        if service:
            out.add(service)
    return out


def normalize_services_list(values: Any) -> list[str]:
    """
    Normalize server service names to a lowercase list preserving input order.
    Accepted inputs: list/tuple/set. Other types return an empty list.
    """
    if not isinstance(values, (list, tuple, set)):
        return []
    out: list[str] = []
    for item in values:
        service = str(item or "").strip().lower()
        if service:
            out.append(service)
    return out


def has_service(source: Any, service_name: str, *, key: str = "server_services") -> bool:
    """
    Check whether a service is enabled in a service collection or in a device config dict.
    """
    target = str(service_name or "").strip().lower()
    if not target:
        return False
    values = source.get(key) if isinstance(source, dict) else source
    return target in normalize_services(values)
