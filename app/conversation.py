# app/conversation.py
# Interactive conversation handler for chat mode
# Improved with follow-up/correction detection and topic-aware refetching

import logging
from typing import Optional
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)

from . import reddit_client as rc
from .nlu import (
    parse_user_query, ParsedQuery, get_greeting_message, get_help_message,
    is_correction_or_refinement, extract_time_range, extract_topic_with_entities,
    map_topic_to_subreddits
)
from .ai_engine import generate_response
from .user_preferences import (
    load_preferences, save_preferences, get_preferences_summary,
    add_favorite_topic, enable_weekly_digest, disable_weekly_digest,
    UserPreferences
)
from .cache import get_cached, set_cached
from .formatter import (
    print_markdown, print_panel, print_response, print_error,
    print_info, print_success, print_warning, print_posts_table,
    print_thinking, print_divider
)


# =============================================================================
# Conversation Context
# =============================================================================

@dataclass
class ConversationContext:
    """Maintains conversation state across messages."""
    last_query: Optional[ParsedQuery] = None
    last_posts: list = field(default_factory=list)
    last_topic: str = ""
    last_time_range: str = "day"
    last_user_message: str = ""
    message_count: int = 0


# =============================================================================
# Follow-up Detection & Merging
# =============================================================================

# Patterns that indicate modification of time range
TIME_CHANGE_PATTERNS = [
    (r"\b(this |last |past |)(hour)\b", "hour"),
    (r"\b(today|this day|24 hours)\b", "day"),
    (r"\b(this |last |past |)(week|weekly|7 days)\b", "week"),
    (r"\b(this |last |past |)(month|monthly|30 days)\b", "month"),
    (r"\b(this |last |past |)(year|yearly)\b", "year"),
]

# Patterns indicating user wants same topic but different params
SAME_TOPIC_MODIFIERS = [
    r"^(ok|okay|sure|alright)[,.]?\s*",
    r"(same|that) (but|for)",
    r"(change|switch) (it |the time |)(to|for)",
    r"(now|instead) (for|try|show)",
]


def detect_time_change(message: str) -> Optional[str]:
    """Extract a time range modification from a message."""
    msg_lower = message.lower()
    
    for pattern, time_range in TIME_CHANGE_PATTERNS:
        if re.search(pattern, msg_lower):
            return time_range
    
    return None


def detect_topic_correction(message: str) -> Optional[tuple[str, list[str]]]:
    """
    Check if user is correcting the topic.
    Returns (new_topic, entities) if detected, else None.
    """
    # Phrases that indicate correction
    correction_phrases = [
        r"i (meant|mean|was asking about|want)",
        r"no[,.]?\s*(i'?m |i was )?(asking|talking) about",
        r"(not .+[,.]?\s*)?(i want|give me|show me|focus on)",
        r"(switch|change) (to|the topic to)",
        r"actually[,.]?\s*(i'?m |i was )?(asking|talking) about",
    ]
    
    msg_lower = message.lower()
    
    is_correction = any(re.search(p, msg_lower) for p in correction_phrases)
    
    if is_correction or len(msg_lower.split()) <= 8:
        # Try to extract a new topic from the message
        new_topic, entities, _confidence = extract_topic_with_entities(message)
        if new_topic != "tech" or entities:  # Found something specific
            return new_topic, entities
    
    return None


def is_simple_continuation(message: str) -> bool:
    """Check if message is just asking for more/continuation."""
    patterns = [
        r"^(more|continue|go on|keep going|and\?|else\?)(\s|$)",
        r"^(what else|anything else|more details)(\?)?$",
        r"^(tell me more|expand|elaborate)(\?)?$",
    ]
    msg_lower = message.lower().strip()
    return any(re.search(p, msg_lower) for p in patterns)


def classify_followup(message: str, has_previous: bool) -> str:
    """
    Classify a follow-up message type.
    Returns: 'time_change', 'topic_correction', 'continuation', 'new_query'
    """
    if not has_previous:
        return "new_query"
    
    msg_lower = message.lower().strip()
    
    # Check for simple continuations first
    if is_simple_continuation(message):
        return "continuation"
    
    # Check for topic corrections
    topic_correction = detect_topic_correction(message)
    if topic_correction:
        return "topic_correction"
    
    # Check for time modifications (in context of previous query)
    time_change = detect_time_change(message)
    if time_change:
        # Check if it looks like a modification of previous, not new query
        for pattern in SAME_TOPIC_MODIFIERS:
            if re.search(pattern, msg_lower):
                return "time_change"
        # Short message with just time = probably time change
        if len(msg_lower.split()) <= 5:
            return "time_change"
    
    # Check for correction/refinement patterns
    if is_correction_or_refinement(message):
        return "topic_correction"
    
    return "new_query"


def merge_with_previous(
    new_message: str,
    previous: ParsedQuery,
    follow_type: str
) -> ParsedQuery:
    """
    Merge a follow-up message with the previous query.
    Returns a modified ParsedQuery based on follow_type.
    """
    # Start with previous query as base
    merged = ParsedQuery(
        topic=previous.topic,
        subreddits=previous.subreddits.copy(),
        time_range=previous.time_range,
        intent=previous.intent,
        original_query=new_message,
        language=previous.language,
        limit=previous.limit,
        detected_entities=previous.detected_entities.copy() if previous.detected_entities else [],
        confidence=previous.confidence
    )
    
    if follow_type == "time_change":
        # Only change the time range
        new_time = detect_time_change(new_message)
        if new_time:
            merged.time_range = new_time
    
    elif follow_type == "topic_correction":
        # Change the topic
        result = detect_topic_correction(new_message)
        if result:
            new_topic, entities = result
            merged.topic = new_topic
            merged.subreddits = map_topic_to_subreddits(new_topic, entities)
            merged.detected_entities = entities
            # Recalculate confidence for the new topic — don't inherit stale confidence
            merged.confidence = "high" if entities else "medium"
    
    elif follow_type == "continuation":
        # Keep everything, just increase the limit
        merged.limit = min(previous.limit + 5, 20)
    
    return merged


# =============================================================================
# Safe Fallback Response (Stage 2)
# =============================================================================

def get_safe_fallback_response(query_terms: str) -> str:
    """
    Return a helpful response when the NLU cannot confidently match a topic.
    This prevents the system from fetching and summarizing irrelevant content.
    """
    return f"""I don't have coverage for **"{query_terms}"** right now.

This usually means the topic isn't in my current knowledge base.

**What you can try:**
- Rephrase with a broader topic (e.g., "gaming news" instead of a specific game title)
- Mention a well-known entity I might recognize (e.g., "Elden Ring", "Bitcoin", "GPT-4")
- Type `/topics` to see what topics I currently cover

I'm being expanded to cover more topics soon!"""


# =============================================================================
# Conversation Handler
# =============================================================================

class ConversationHandler:
    """Handles interactive conversation with the user."""
    
    def __init__(self):
        self.context = ConversationContext()
        self.preferences = load_preferences()
    
    def reset(self):
        """Clear conversation history."""
        self.context = ConversationContext()
        print_info("Conversation reset")
    
    def _handle_command(self, command: str) -> tuple[bool, str]:
        """Handle special commands. Returns (handled, response)."""
        cmd = command.lower().strip()
        
        # Quit commands
        if cmd in ["/quit", "/exit", "quit", "exit", "q"]:
            return True, "__QUIT__"
        
        # Help commands
        if cmd in ["/help", "help", "?"]:
            return True, get_help_message()
        
        # Settings commands
        if cmd in ["/settings", "settings"]:
            return True, get_preferences_summary("en")
        
        # Topic list
        if cmd in ["/topics", "topics"]:
            topics_msg = """
## Available Topics

| Topic | Example Keywords | Entities I Recognize |
|-------|------------------|---------------------|
| **AI** | ai, machine learning, llm | GPT-4, Claude, Gemini, Llama, Midjourney |
| **Tech** | technology, gadgets, hardware | Apple, Nvidia, iPhone, Android, M3 chip |
| **Programming** | coding, developer, web dev | Python, JavaScript, React, Docker, GitHub |
| **Sports** | football, basketball, nba | Lakers, Real Madrid, Messi, Champions League |
| **Politics** | government, elections, vote | Trump, Biden, EU, NATO, Supreme Court |
| **Gaming** | video games, esports | Baldur's Gate 3, Elden Ring, PS5, Steam |
| **Crypto** | blockchain, defi, nft | Bitcoin, Ethereum, Solana, Coinbase |
| **Science** | research, physics, space | NASA, SpaceX, James Webb, CERN |

Just ask about any of these naturally!
"""
            return True, topics_msg
        
        # Weekly digest toggle
        if cmd in ["/weekly on", "weekly on"]:
            enable_weekly_digest(self.preferences.favorite_topics)
            return True, "✅ Weekly digest enabled!"
        
        if cmd in ["/weekly off", "weekly off"]:
            disable_weekly_digest()
            return True, "Weekly digest disabled"
        
        # Clear cache
        if cmd in ["/clear cache", "clear cache", "/cache clear"]:
            from .cache import clear_cache
            count = clear_cache()
            return True, f"Cleared {count} cache files"
        
        # Reset conversation
        if cmd in ["/reset", "reset", "/new", "new", "/clear"]:
            self.reset()
            return True, "🔄 Conversation reset. What would you like to know?"
        
        return False, ""
    
    def _fetch_posts(self, parsed: ParsedQuery, use_cache: bool = True,
                     digest_search_query: Optional[str] = None) -> list:
        """Fetch posts for the given query, using cache if available.
        
        Args:
            digest_search_query: When set, forces active search mode using this
                string as the Reddit search query. Used by explicit subreddit
                digests so they retrieve focused content instead of generic top
                listings.
        """
        
        # Determine retrieval mode: active search vs passive listing
        use_search_mode = False
        if digest_search_query:
            use_search_mode = True
        elif parsed.detected_entities:
            use_search_mode = True
        elif parsed.intent in ["compare", "shopping", "drama", "help"]:
            use_search_mode = True
            
        search_query = digest_search_query or (parsed.original_query if use_search_mode else None)
        
        cache_key_params = {
            'subreddits': tuple(sorted(parsed.subreddits)),
            'time_range': parsed.time_range,
            'limit': parsed.limit,
            'topic': parsed.topic,
            'entities': tuple(sorted(parsed.detected_entities)) if parsed.detected_entities else (),
            'search_query': search_query
        }
        
        # Check cache first
        if use_cache and self.preferences.cache_enabled:
            cached = get_cached(
                'posts',
                max_age_hours=self.preferences.cache_duration_hours,
                **cache_key_params
            )
            if cached:
                logger.info(
                    "[CONV] Cache hit: topic=%s, subreddits=%s, posts=%d",
                    parsed.topic, parsed.subreddits, len(cached)
                )
                print_info("Using cached data")
                return cached
        
        # Fetch from Reddit - balance breadth vs speed
        all_posts = []
        subreddits_to_try = parsed.subreddits[:3]  # Limit to 3 subreddits for speed
        is_primary_weighted = bool(digest_search_query) and len(subreddits_to_try) > 1
        
        logger.info(
            "[CONV] Fetching posts: subreddits=%s, time=%s, topic=%s, "
            "search_mode=%s, primary_weighted=%s",
            subreddits_to_try, parsed.time_range, parsed.topic,
            use_search_mode, is_primary_weighted
        )
        
        for idx, subreddit in enumerate(subreddits_to_try):
            # Fix 3: Primary sub gets more posts; fallback subs get fewer
            is_primary = (idx == 0)
            if is_primary_weighted:
                per_sub_limit = 8 if is_primary else 3
            else:
                per_sub_limit = 10 if parsed.time_range == "week" else 5
            
            try:
                if use_search_mode:
                    logger.debug("[CONV] Active Search mode in r/%s for query='%s' (limit=%d)",
                                 subreddit, search_query, per_sub_limit)
                    posts = rc.get_search_posts(
                        subreddit=subreddit,
                        query=search_query,
                        limit=per_sub_limit,
                        time_filter=parsed.time_range,
                        with_comments=True
                    )
                else:
                    logger.debug("[CONV] Passive Listing mode in r/%s (limit=%d)", subreddit, per_sub_limit)
                    posts = rc.get_posts_with_comments(
                        subreddit=subreddit,
                        sort="top",
                        time_filter=parsed.time_range,
                        requested=per_sub_limit,
                        comment_limit=3,  # Fewer comments for speed
                        min_score=None  # No score filter for broader results
                    )
                all_posts.extend(posts)
                logger.debug(
                    "[CONV] Fetched %d posts from r/%s",
                    len(posts), subreddit
                )
            except Exception as e:
                logger.warning(
                    "[CONV] Failed to fetch from r/%s: %s",
                    subreddit, e
                )
                print_warning(f"Could not fetch from r/{subreddit}: {e}")
        
        all_posts.sort(key=lambda p: p.get('score', 0), reverse=True)
        # Keep up to configured posts for AI
        max_total = 15 if parsed.time_range == "week" else 10
        all_posts = all_posts[:max_total]
        
        logger.info(
            "[CONV] Fetch complete: total_posts=%d, topic=%s, subreddits=%s",
            len(all_posts), parsed.topic, subreddits_to_try
        )
        
        # Cache the results
        if self.preferences.cache_enabled and all_posts:
            set_cached(all_posts, 'posts', **cache_key_params)
        
        return all_posts
    
    def _try_broader_search(self, parsed: ParsedQuery, min_wanted: int = 3) -> tuple[list, str]:
        """
        If initial search yields few posts, try broadening within the same domain.
        Returns (posts, adjustment_message).
        """
        adjustment_msg = ""
        
        # First try extending time range
        time_progressions = {
            "hour": "day",
            "day": "week",
            "week": "month",
        }
        
        if parsed.time_range in time_progressions:
            new_time = time_progressions[parsed.time_range]
            broader_query = ParsedQuery(
                topic=parsed.topic,
                subreddits=parsed.subreddits,
                time_range=new_time,
                intent=parsed.intent,
                original_query=parsed.original_query,
                language=parsed.language,
                limit=parsed.limit,
                detected_entities=parsed.detected_entities,
                confidence=parsed.confidence
            )
            posts = self._fetch_posts(broader_query, use_cache=True)
            if len(posts) >= min_wanted:
                adjustment_msg = f"(Expanded search to {new_time} to find more posts)"
                return posts, adjustment_msg
        
        return [], ""
    
    def process_message(self, user_message: str, override_subreddits: Optional[list[str]] = None) -> str:
        """Process a user message and return the response."""
        self.context.message_count += 1
        
        # Check for commands first
        handled, response = self._handle_command(user_message)
        if handled:
            return response
        
        # Classify the message type
        has_previous = self.context.last_query is not None
        follow_type = classify_followup(user_message, has_previous)
        
        # Build the query based on classification
        if follow_type in ["time_change", "topic_correction", "continuation"] and has_previous:
            print_info(f"Interpreting as {follow_type.replace('_', ' ')}...")
            parsed = merge_with_previous(user_message, self.context.last_query, follow_type)
        else:
            parsed = parse_user_query(user_message)
            
        # === Digest override: normalize subreddits, fix intent, build search query ===
        digest_search_query = None  # Set when override triggers active search
        
        if override_subreddits:
            from .nlu import normalize_entity
            from .registry import ENTITY_SUBREDDIT_OVERRIDES
            
            normalized_subs = []
            primary_community = None  # The canonical name for the primary community
            
            for sub in override_subreddits:
                norm = normalize_entity(sub)
                if norm in ENTITY_SUBREDDIT_OVERRIDES:
                    override_list = ENTITY_SUBREDDIT_OVERRIDES[norm]
                    for s in override_list:
                        if s not in normalized_subs:
                            normalized_subs.append(s)
                    # The first entry in the override is the primary community
                    if primary_community is None:
                        primary_community = norm  # e.g. "teamfight tactics", "real madrid"
                else:
                    # Fallback: strip spaces to make url-safe for PRAW
                    cleaned = sub.replace(" ", "").replace("r/", "").replace("R/", "")
                    if cleaned and cleaned not in normalized_subs:
                        normalized_subs.append(cleaned)
                    if primary_community is None:
                        primary_community = sub.strip()
                        
            parsed.subreddits = normalized_subs
            
            # Fix 1: Force summarize intent — digest should never use help template
            parsed.intent = "summarize"
            
            # Fix 4: Build a focused search query from the primary community name
            # This drives active search instead of passive listing
            digest_search_query = primary_community or (normalized_subs[0] if normalized_subs else None)
            
            logger.info(
                "[CONV] Digest override applied: normalized_subs=%s, "
                "primary_community='%s', intent=%s, search_query='%s'",
                normalized_subs, primary_community, parsed.intent, digest_search_query
            )
        
        # Store previous context before updating
        previous_question = self.context.last_user_message
        previous_topic = self.context.last_topic
        previous_time_range = self.context.last_time_range
        
        # Update context with new query
        self.context.last_query = parsed
        self.context.last_topic = parsed.topic
        self.context.last_time_range = parsed.time_range
        self.context.last_user_message = user_message
        
        # Show thinking indicator
        print_thinking()
        
        # === STAGE 4: Dynamic Search Fallback ===
        is_global_search = False
        adjustment_msg = ""
        
        if parsed.confidence == "default" and not override_subreddits:
            query_terms = user_message.strip()
            logger.info(
                "[CONV] Confidence is DEFAULT. Falling back to global search for: '%s'",
                query_terms[:60]
            )
            from .reddit_client import global_search
            # Perform global search instead of failing immediately
            posts = global_search(query_terms, limit=10, time_filter=parsed.time_range)
            is_global_search = True
            
            if not posts:
                # Still nothing found? Fall back to safety message
                logger.warning("[CONV] Global search yielded 0 posts. Triggering fail-soft.")
                return get_safe_fallback_response(query_terms)
        else:
            # Fetch posts using normal targeted routing (or overridden subreddits)
            posts = self._fetch_posts(parsed, digest_search_query=digest_search_query)
            
            # If too few posts, try broadening within same domain
            min_wanted = 10 if parsed.time_range == "week" else 5
            if len(posts) < min_wanted:
                broader_posts, adjustment_msg = self._try_broader_search(parsed, min_wanted)
                if broader_posts:
                    posts = broader_posts
        
        self.context.last_posts = posts
        
        logger.info(
            "[CONV] Pipeline: query='%s', follow_type=%s, topic=%s, "
            "entities=%s, subreddits=%s, posts_fetched=%d%s",
            user_message[:60], follow_type, parsed.topic,
            parsed.detected_entities, parsed.subreddits,
            len(posts),
            f", broadened: {adjustment_msg}" if adjustment_msg else ""
        )
        
        # Show posts table
        if posts:
            print_posts_table(posts)
            if adjustment_msg:
                print_info(adjustment_msg)
        
        # Generate AI response
        is_followup = follow_type in ["time_change", "topic_correction", "continuation"]
        
        try:
            # Fix 2: Build clear prompt topic from normalized subreddit names
            prompt_topic = parsed.topic
            if override_subreddits and parsed.subreddits:
                primary_sub = parsed.subreddits[0]  # e.g. "realmadrid", "TeamfightTactics"
                if len(parsed.subreddits) > 1:
                    others = ', r/'.join(parsed.subreddits[1:3])
                    prompt_topic = f"r/{primary_sub} (with supplementary content from r/{others})"
                else:
                    prompt_topic = f"r/{primary_sub}"
                
            response = generate_response(
                user_question=user_message,
                posts=posts,
                topic=prompt_topic,
                time_range=parsed.time_range,
                intent=parsed.intent,
                detected_entities=parsed.detected_entities,
                is_followup=is_followup,
                previous_question=previous_question,
                previous_topic=previous_topic,
                previous_time_range=previous_time_range,
                follow_type=follow_type,
                is_global_search=is_global_search,
                skip_mismatch_check=bool(override_subreddits)
            )
            return response
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def get_welcome_message(self) -> str:
        """Get the welcome/greeting message."""
        return get_greeting_message()


# =============================================================================
# Interactive Chat Loop
# =============================================================================

def run_interactive_chat():
    """Run the interactive chat loop."""
    from .formatter import (
        print_welcome, print_response, print_error, 
        get_user_input, print_goodbye
    )
    
    # Initialize handler
    handler = ConversationHandler()
    
    # Print welcome
    print_welcome()
    print_markdown(handler.get_welcome_message())
    print_divider()
    
    # Main loop
    while True:
        try:
            # Get user input
            user_input = get_user_input()
            
            if not user_input:
                continue
            
            # Process message
            response = handler.process_message(user_input)
            
            # Check for quit
            if response == "__QUIT__":
                print_goodbye()
                break
            
            # Print response
            print_response(response)
            print_divider()
            
        except KeyboardInterrupt:
            print_goodbye()
            break
        except Exception as e:
            print_error(str(e))
