# backend/app/services/pkt_generator/template.py
from __future__ import annotations

import os
import logging
from functools import lru_cache
from pathlib import Path

from .generator import PKTGenerator

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_pkt_generator(template_path: str) -> PKTGenerator:
    logger.info("Loading PKT generator template in cache from %s", template_path)
    return PKTGenerator(template_path)


def get_template_path() -> Path:
    # 1. Check environment variable
    env_template = os.environ.get("PKT_TEMPLATE_PATH")
    if env_template and Path(env_template).exists():
        return Path(env_template)

    # 2. Check relative to this file (assuming structure: backend/app/services/pkt_generator/template.py)
    # Move up: template.py -> pkt_generator -> services -> app -> backend
    candidate = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "simple_ref.pkt"
    if candidate.exists():
        return candidate

    # 3. Check relative to current working directory
    # If in 'backend' folder
    candidate = Path.cwd() / "templates" / "simple_ref.pkt"
    if candidate.exists():
        return candidate
        
    # If in 'backend/app' folder
    candidate = Path.cwd().parent / "templates" / "simple_ref.pkt"
    if candidate.exists():
        return candidate

    # 4. Fallback for Docker
    docker_path = Path("/app/templates/simple_ref.pkt")
    if docker_path.exists():
        return docker_path

    raise FileNotFoundError("simple_ref.pkt template not found. Set PKT_TEMPLATE_PATH env variable.")
