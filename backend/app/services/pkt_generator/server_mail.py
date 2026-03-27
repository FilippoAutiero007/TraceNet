from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


_EMAIL_SERVICES = {"smtp", "pop3", "email"}


def get_mail_users_and_domain(dev_cfg: dict[str, Any]) -> tuple[list[dict[str, str]], str]:
    domain = str(dev_cfg.get("mail_domain") or "").strip() or "mail.local"

    users: list[dict[str, str]] = []
    raw_users = dev_cfg.get("mail_users")
    if isinstance(raw_users, list):
        for raw_user in raw_users:
            if not isinstance(raw_user, dict):
                continue
            username = str(raw_user.get("username") or "").strip()
            if not username:
                continue
            password = str(raw_user.get("password") or "1234").strip() or "1234"
            users.append({"username": username, "password": password})

    if not users:
        users = [
            {"username": "user1", "password": "1234"},
            {"username": "user2", "password": "1234"},
        ]
    return users, domain


def _is_email_service_enabled(services: set[str]) -> bool:
    return bool(services.intersection(_EMAIL_SERVICES))


def _set_text(parent: ET.Element, tag: str, value: str) -> None:
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    node.text = value


def write_email_config(engine: ET.Element, dev_cfg: dict[str, Any]) -> None:
    services_raw = dev_cfg.get("server_services")
    services: set[str] = set()
    if isinstance(services_raw, (list, set, tuple)):
        services = {str(s).strip().lower() for s in services_raw if str(s).strip()}

    smtp = engine.find("SMTP_SERVER")
    pop3 = engine.find("POP3_SERVER")

    if services and not _is_email_service_enabled(services):
        for node in (smtp, pop3):
            if node is None:
                continue
            _set_text(node, "ENABLED", "0")
        return

    users, domain = get_mail_users_and_domain(dev_cfg)

    for node in (smtp, pop3):
        if node is None:
            continue
        _set_text(node, "ENABLED", "1")
        _set_text(node, "DOMAIN", domain)

        mgr = node.find("USER_ACCOUNT_MNGR")
        if mgr is None:
            mgr = ET.SubElement(node, "USER_ACCOUNT_MNGR")
        mgr.clear()

        for user in users:
            acct = ET.SubElement(mgr, "ACCOUNT")
            ET.SubElement(acct, "USERNAME").text = user["username"]
            ET.SubElement(acct, "PASSWORD").text = user["password"]

