# app/conversation.py
# Interactive conversation handler for chat mode
# Improved with follow-up/correction detection and topic-aware refetching

from typing import Optional
from dataclasses import dataclass, field
import re

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
        new_topic, entities = extract_topic_with_entities(message)
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
        detected_entities=previous.detected_entities.copy() if previous.detected_entities else []
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
    
    elif follow_type == "continuation":
        # Keep everything, just increase the limit
        merged.limit = min(previous.limit + 5, 20)
    
    return merged


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
    
    def _fetch_posts(self, parsed: ParsedQuery, use_cache: bool = True) -> list:
        """Fetch posts for the given query, using cache if available."""
        cache_key_params = {
            'subreddits': tuple(sorted(parsed.subreddits)),
            'time_range': parsed.time_range,
            'limit': parsed.limit,
            'topic': parsed.topic,
            'entities': tuple(sorted(parsed.detected_entities)) if parsed.detected_entities else ()
        }
        
        # Check cache first
        if use_cache and self.preferences.cache_enabled:
            cached = get_cached(
                'posts',
                max_age_hours=self.preferences.cache_duration_hours,
                **cache_key_params
            )
            if cached:
                print_info("Using cached data")
                return cached
        
        # Fetch from Reddit - balance breadth vs speed
        all_posts = []
        subreddits_to_try = parsed.subreddits[:3]  # Limit to 3 subreddits for speed
        
        for subreddit in subreddits_to_try:
            try:
                posts = rc.get_posts_with_comments(
                    subreddit=subreddit,
                    sort="top",
                    time_filter=parsed.time_range,
                    requested=5,  # 5 posts per subreddit
                    comment_limit=3,  # Fewer comments for speed
                    min_score=None  # No score filter for broader results
                )
                all_posts.extend(posts)
            except Exception as e:
                print_warning(f"Could not fetch from r/{subreddit}: {e}")
        
        all_posts.sort(key=lambda p: p.get('score', 0), reverse=True)
        # Keep up to 10 posts for AI
        all_posts = all_posts[:10]
        
        # Cache the results
        if self.preferences.cache_enabled and all_posts:
            set_cached(all_posts, 'posts', **cache_key_params)
        
        return all_posts
    
    def _try_broader_search(self, parsed: ParsedQuery) -> tuple[list, str]:
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
                detected_entities=parsed.detected_entities
            )
            posts = self._fetch_posts(broader_query, use_cache=True)
            if len(posts) >= 3:
                adjustment_msg = f"(Expanded search to {new_time} to find more posts)"
                return posts, adjustment_msg
        
        return [], ""
    
    def process_message(self, user_message: str) -> str:
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
        
        # Fetch posts
        posts = self._fetch_posts(parsed)
        
        # If too few posts, try broadening within same domain
        adjustment_msg = ""
        if len(posts) < 3:
            broader_posts, adjustment_msg = self._try_broader_search(parsed)
            if broader_posts:
                posts = broader_posts
        
        self.context.last_posts = posts
        
        # Show posts table
        if posts:
            print_posts_table(posts)
            if adjustment_msg:
                print_info(adjustment_msg)
        
        # Generate AI response
        is_followup = follow_type in ["time_change", "topic_correction", "continuation"]
        
        try:
            response = generate_response(
                user_question=user_message,
                posts=posts,
                topic=parsed.topic,
                time_range=parsed.time_range,
                intent=parsed.intent,
                detected_entities=parsed.detected_entities,
                is_followup=is_followup,
                previous_question=previous_question,
                previous_topic=previous_topic,
                previous_time_range=previous_time_range,
                follow_type=follow_type
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
