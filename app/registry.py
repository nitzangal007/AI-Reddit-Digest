# app/registry.py
# Entity registry loader — loads topic/entity/alias data from external JSON
# Stage 3A: All routing data externalized to data/entity_registry.json

import json
import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)

# =============================================================================
# Registry Loading
# =============================================================================

_REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "entity_registry.json"
)


def _load_registry(path: str) -> dict:
    """Load and validate the entity registry from JSON."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("[REGISTRY] Registry file not found: %s", path)
        raise SystemExit(f"Entity registry not found at {path}")
    except json.JSONDecodeError as e:
        logger.error("[REGISTRY] Malformed JSON in registry: %s", e)
        raise SystemExit(f"Malformed entity registry JSON: {e}")

    # Validate required top-level keys
    required_keys = ["topics", "entity_subreddit_overrides", "aliases"]
    for key in required_keys:
        if key not in data:
            logger.error("[REGISTRY] Missing required key: %s", key)
            raise SystemExit(f"Entity registry missing required key: '{key}'")

    return data


def _build_topic_keywords(topics: dict) -> Dict[str, Dict[str, List[str]]]:
    """Convert topics section into TOPIC_KEYWORDS format used by NLU."""
    result = {}
    for topic_name, topic_data in topics.items():
        result[topic_name] = {
            "keywords": topic_data.get("keywords", []),
            "entities": topic_data.get("entities", []),
        }
    return result


def _build_topic_subreddit_map(topics: dict) -> Dict[str, List[str]]:
    """Extract default_subreddits from topics into TOPIC_SUBREDDIT_MAP format."""
    result = {}
    for topic_name, topic_data in topics.items():
        default_subs = topic_data.get("default_subreddits", [])
        if default_subs:
            result[topic_name] = default_subs
    return result


# =============================================================================
# Load and Export
# =============================================================================

_registry = _load_registry(_REGISTRY_PATH)

# These are the 4 data structures consumed by nlu.py and config.py
TOPIC_KEYWORDS: Dict[str, Dict[str, List[str]]] = _build_topic_keywords(_registry["topics"])
ENTITY_SUBREDDIT_OVERRIDES: Dict[str, List[str]] = _registry["entity_subreddit_overrides"]
ENTITY_ALIASES: Dict[str, str] = _registry["aliases"]
TOPIC_SUBREDDIT_MAP: Dict[str, List[str]] = _build_topic_subreddit_map(_registry["topics"])

# Log registry stats on load
logger.info(
    "[REGISTRY] Loaded: %d topics, %d entity overrides, %d aliases, %d topic subreddit maps",
    len(TOPIC_KEYWORDS), len(ENTITY_SUBREDDIT_OVERRIDES),
    len(ENTITY_ALIASES), len(TOPIC_SUBREDDIT_MAP)
)


def reload_registry():
    """Reload the registry from disk (for future hot-reload support)."""
    global TOPIC_KEYWORDS, ENTITY_SUBREDDIT_OVERRIDES, ENTITY_ALIASES, TOPIC_SUBREDDIT_MAP
    registry = _load_registry(_REGISTRY_PATH)
    TOPIC_KEYWORDS = _build_topic_keywords(registry["topics"])
    ENTITY_SUBREDDIT_OVERRIDES = registry["entity_subreddit_overrides"]
    ENTITY_ALIASES = registry["aliases"]
    TOPIC_SUBREDDIT_MAP = _build_topic_subreddit_map(registry["topics"])
    logger.info("[REGISTRY] Reloaded successfully")
