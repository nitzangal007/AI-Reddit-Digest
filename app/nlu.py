# app/nlu.py
# Natural Language Understanding - Parse user queries to extract intent, topic, and time range
# Comprehensive entity-aware detection for all topics

import re
import logging
from dataclasses import dataclass
from typing import Literal, Optional, List, Dict
from .registry import TOPIC_KEYWORDS, ENTITY_SUBREDDIT_OVERRIDES, ENTITY_ALIASES, TOPIC_SUBREDDIT_MAP

logger = logging.getLogger(__name__)

TimeRange = Literal["hour", "day", "week", "month", "year", "all"]
Intent = Literal["summarize", "highlights", "trending", "compare", "help", "settings"]


@dataclass
class ParsedQuery:
    """Parsed user query with extracted parameters."""
    topic: str                      # e.g., "ai", "tech"
    subreddits: list[str]           # e.g., ["MachineLearning", "ChatGPT"]
    time_range: TimeRange           # e.g., "week"
    intent: Intent                  # e.g., "summarize"
    original_query: str             # Original user input
    language: str                   # Always "en"
    limit: int                      # Number of posts to fetch
    detected_entities: list[str]    # Specific entities found (games, coins, models, etc.)
    confidence: str = "medium"      # "high", "medium", or "default" — how confident the NLU match is



# =============================================================================
# TIME RANGE EXTRACTION
# =============================================================================

TIME_PATTERNS = {
    "hour": [r"last hour", r"past hour", r"this hour", r"1 hour", r"one hour"],
    "day": [r"\btoday\b", r"last day", r"past day", r"24 hours", r"this day"],
    "week": [r"this week", r"last week", r"past week", r"\bweekly\b", r"7 days"],
    "month": [r"this month", r"last month", r"past month", r"\bmonthly\b", r"30 days"],
    "year": [r"this year", r"last year", r"past year", r"\byearly\b", r"12 months"],
}


def extract_time_range(query: str) -> TimeRange:
    """Extract time range from query, default to 'day'."""
    query_lower = query.lower()
    
    for time_range, patterns in TIME_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return time_range
    
    return "day"


# =============================================================================
# TOPIC EXTRACTION
# =============================================================================

def extract_topic_with_entities(query: str) -> tuple[str, list[str], str]:
    """
    Extract topic using both keywords and entity matching.
    Returns (topic, list_of_detected_entities, confidence).
    Confidence is 'high' (entity match), 'medium' (keyword only), or 'default' (nothing matched).
    """
    query_lower = query.lower()
    
    # 1. Score each topic based on TOPIC_KEYWORDS
    topic_scores: Dict[str, int] = {}
    topic_entities: Dict[str, list[str]] = {}
    
    for topic, patterns in TOPIC_KEYWORDS.items():
        score = 0
        found_entities = []
        
        # Check keywords (lower weight)
        for kw_pattern in patterns.get("keywords", []):
            if re.search(kw_pattern, query_lower, re.IGNORECASE):
                score += 1
        
        # Check entities (higher weight - entities are more specific)
        for entity_pattern in patterns.get("entities", []):
            match = re.search(entity_pattern, query_lower, re.IGNORECASE)
            if match:
                score += 3  # Entities worth more
                found_entities.append(match.group().lower())
        
        if score > 0:
            topic_scores[topic] = score
            topic_entities[topic] = found_entities
            
    # 2. Check all registry explicitly defined overrides/aliases
    orphan_entities = []
    
    # Fast-check loop: check substring first, then word boundaries
    for entity in ENTITY_SUBREDDIT_OVERRIDES:
        if entity in query_lower:
            if re.search(r"\b" + re.escape(entity) + r"\b", query_lower):
                orphan_entities.append(entity)
                
    for alias in ENTITY_ALIASES:
        if alias in query_lower:
            if re.search(r"\b" + re.escape(alias) + r"\b", query_lower):
                orphan_entities.append(alias)
                
    # 3. Determine best topic
    best_topic = None
    if topic_scores:
        best_topic = max(topic_scores, key=topic_scores.get)
    
    # Consolidate entities
    best_entities = topic_entities.get(best_topic, []) if best_topic else []
    # Add orphans (avoid exact duplicates)
    for oe in orphan_entities:
        if oe not in best_entities:
            best_entities.append(oe)
            
    # 4. Determine confidence rating
    if best_entities:
        confidence = "high"
        # If we found an entity but no topic, default it to tech
        # map_topic_to_subreddits will override the topic anyway
        if not best_topic:
            best_topic = "tech"
    elif best_topic:
        confidence = "medium"
    else:
        confidence = "default"
        best_topic = "tech" # safe fallback topic

    if confidence != "default":
        logger.info(
            "[NLU] Topic detected: topic=%s, entities=%s, "
            "match_type=MATCHED, confidence=%s, query='%s'",
            best_topic, best_entities, confidence, query[:80]
        )
    else:
        logger.warning(
            "[NLU] No topic matched — falling back to default: "
            "topic=%s, entities=[], confidence=DEFAULT, query='%s'",
            best_topic, query[:80]
        )

    return best_topic, best_entities, confidence


def normalize_entity(entity: str) -> str:
    """Normalize entity using aliases."""
    lower = entity.lower().strip()
    return ENTITY_ALIASES.get(lower, lower)


def map_topic_to_subreddits(topic: str, entities: list[str] = None) -> list[str]:
    """
    Map topic to subreddits with entity-specific overrides.
    Supports multiple entities (merge + dedupe with priority).
    Uses hybrid mode: combines targeted subs with topic defaults.
    """
    subreddits = []
    
    # Check for entity-specific overrides first
    if entities:
        for entity in entities:
            normalized = normalize_entity(entity)
            if normalized in ENTITY_SUBREDDIT_OVERRIDES:
                # Add entity-specific subs with high priority
                for sub in ENTITY_SUBREDDIT_OVERRIDES[normalized]:
                    if sub not in subreddits:
                        subreddits.append(sub)
                logger.info(
                    "[NLU] Entity override found: entity='%s', normalized='%s', "
                    "subreddits=%s",
                    entity, normalized, ENTITY_SUBREDDIT_OVERRIDES[normalized]
                )
            else:
                logger.debug(
                    "[NLU] Entity '%s' (normalized='%s') has no subreddit override",
                    entity, normalized
                )
    
    # If we found entity-specific subs, return them (up to 4)
    if subreddits:
        selected = subreddits[:4]
        logger.info(
            "[NLU] Subreddit selection: source=ENTITY_OVERRIDE, "
            "subreddits=%s, topic=%s",
            selected, topic
        )
        return selected
    
    # Fall back to topic-level mapping
    fallback_subs = TOPIC_SUBREDDIT_MAP.get(topic, TOPIC_SUBREDDIT_MAP.get("tech", []))
    logger.info(
        "[NLU] Subreddit selection: source=TOPIC_MAP, "
        "subreddits=%s, topic=%s",
        fallback_subs, topic
    )
    return fallback_subs


# =============================================================================
# INTENT EXTRACTION
# =============================================================================

INTENT_PATTERNS = {
    "highlights": [
        r"\bhighlights?\b", r"key points?", r"main points?", r"tldr", r"tl;?dr",
        r"quick (summary|overview)", r"bullet", r"\bbrief\b", r"top \d+", r"best of"
    ],
    "trending": [
        r"\btrending\b", r"\bhot\b", r"\bbuzz\b", r"\bviral\b", r"popular",
        r"controversial", r"debate", r"drama", r"what.+talking about"
    ],
    "compare": [
        r"which (is |are )?(the )?(best|better|preferred|recommended)",
        r"\bcompare\b", r"\bvs\.?\b", r"\bversus\b", r"difference between",
        r"what do (people|users|redditors) (think|prefer|recommend|say)",
        r"opinion on", r"thoughts on", r"how do people feel"
    ],
    "help": [
        r"^help$", r"how (do|can|to)", r"what (is|are) a?\b", r"\bexplain\b",
        r"commands?$", r"what can you"
    ],
    "settings": [
        r"\bsettings?\b", r"\bpreferences?\b", r"configure", r"setup"
    ],
    "summarize": [
        r"summarize", r"summary", r"what (happened|'s new|'s going on)",
        r"update me", r"tell me about", r"give me", r"show me"
    ]
}


def extract_intent(query: str) -> Intent:
    """Extract the user's intent from the query."""
    query_lower = query.lower()
    
    # Check patterns in priority order
    priority_order = ["compare", "highlights", "trending", "help", "settings", "summarize"]
    
    for intent in priority_order:
        patterns = INTENT_PATTERNS.get(intent, [])
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return intent
    
    return "summarize"


# =============================================================================
# LIMIT EXTRACTION
# =============================================================================

def extract_limit(query: str) -> int:
    """Extract number of posts to fetch from query."""
    patterns = [
        r"(\d+)\s*posts?",
        r"top\s*(\d+)",
        r"show\s*(me\s*)?(\d+)",
        r"(\d+)\s*(results?|items?)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            for group in reversed(match.groups()):
                if group and group.isdigit():
                    n = int(group)
                    if 1 <= n <= 50:
                        return n
    
    return 5


# =============================================================================
# FOLLOW-UP / CORRECTION DETECTION
# =============================================================================

CORRECTION_PATTERNS = [
    # Explicit corrections
    r"(that'?s |)(not what i (asked|meant)|wrong topic)",
    r"i (meant|mean|was asking about|want)",
    r"no[,.]?\s*(i'?m |i was )?(asking|talking) about",
    r"not .+[,.]?\s*(i want|give me|show me)",
    # Topic switches within context
    r"(same (question|thing)|that) (but |)(for|about|on|in)",
    r"(now|instead|actually|rather)\s*(for|about|focus on|show me)",
    r"(change|switch) (it |)(to|the topic to)",
    # Time corrections
    r"(ok|okay|sure|alright)[,.]?\s*(so |now )?(change|switch|try|make it|do)",
    r"(same|that) (but |)(for |about |)(this |last |the |)(week|month|year|day)",
    r"(for |)(this |last |)(week|month|year)( instead)?$",
]


def is_correction_or_refinement(message: str) -> bool:
    """Check if this message is a correction or refinement of previous query."""
    msg_lower = message.lower().strip()
    
    for pattern in CORRECTION_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return True
    
    # Very short messages starting with "ok", "no", "not" are likely corrections
    if len(msg_lower.split()) <= 6:
        if re.match(r"^(ok|okay|no|not|actually|i meant|same but)", msg_lower):
            return True
    
    return False


# =============================================================================
# MAIN PARSER
# =============================================================================

def parse_user_query(query: str) -> ParsedQuery:
    """Parse a natural language query and extract all relevant parameters."""
    topic, detected_entities, confidence = extract_topic_with_entities(query)
    subreddits = map_topic_to_subreddits(topic, detected_entities)
    time_range = extract_time_range(query)
    intent = extract_intent(query)
    limit = extract_limit(query)
    
    parsed = ParsedQuery(
        topic=topic,
        subreddits=subreddits,
        time_range=time_range,
        intent=intent,
        original_query=query,
        language="en",
        limit=limit,
        detected_entities=detected_entities,
        confidence=confidence
    )
    
    logger.info(
        "[NLU] Parsed query: topic=%s, intent=%s, time=%s, "
        "entities=%s, confidence=%s, subreddits=%s, query='%s'",
        topic, intent, time_range, detected_entities,
        confidence, subreddits, query[:80]
    )
    
    return parsed


# =============================================================================
# MESSAGES
# =============================================================================

def get_greeting_message() -> str:
    """Get a greeting message."""
    return """
## Welcome to Reddit Digest!

I'm here to help you stay updated on what's happening on Reddit!

**What I can do:**
- Summarize what happened today/this week on any topic
- Find the most interesting posts and highlights
- Show what's trending or controversial
- Compare opinions (e.g., "which AI model do people prefer?")

**Topics I know:**
Tech, AI, Programming, Sports, Politics, Gaming, Crypto, Science

**Example questions:**
- "What happened this week in AI?"
- "What's trending in the Premier League today?"
- "Which crypto coins are people talking about?"
- "Give me gaming highlights from this month"
- "What do Redditors think about Python vs JavaScript?"

Just ask me anything!
"""


def get_help_message() -> str:
    """Get a help message."""
    return """
## Help - Reddit Digest

**Commands:**
- `/help` - Show this message
- `/topics` - Show available topics
- `/settings` - View preferences
- `/weekly on/off` - Toggle weekly digest
- `/reset` - Clear conversation context
- `/quit` - Exit

**Tips:**
- I understand team names (Lakers, Real Madrid), game titles (Elden Ring), crypto coins (Solana), AI models (Claude, GPT-4), and more.
- Specify time: "today", "this week", "this month"
- Ask for highlights: "give me the highlights"
- Ask for trending: "what's hot", "what's controversial"
- If I get the topic wrong, just say "I meant [topic]" and I'll correct it.

**Examples:**
- "What's the buzz around Baldur's Gate 3?"
- "Bitcoin news this week"
- "Champions League highlights"
"""
