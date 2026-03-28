# app/ai_engine.py
# AI Summarization Engine using Google Gemini
# Universal topic-aware prompts, mismatch detection, and grounded responses

import logging
from datetime import datetime
from google.api_core import exceptions as google_exceptions
import google.generativeai as genai
from typing import Optional, List, Dict
from dataclasses import dataclass
from .config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FALLBACK_MODELS
from .reddit_client import PostData

logger = logging.getLogger(__name__)

# =============================================================================
# Gemini Configuration
# =============================================================================

def configure_gemini():
    """Initialize the Gemini API with the API key."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required. Add it to your .env file.")
    genai.configure(api_key=GEMINI_API_KEY)

def get_gemini_model(model_name: str = GEMINI_MODEL):
    """Get the configured Gemini model."""
    configure_gemini()
    return genai.GenerativeModel(model_name)

# =============================================================================
# Multi-Model Fallback Telemetry (In-Memory)
# =============================================================================

_model_call_stats: Dict[str, Dict[str, int]] = {
    GEMINI_MODEL: {"success": 0, "quota_error": 0, "other_error": 0}
}
for fm in GEMINI_FALLBACK_MODELS:
    if fm not in _model_call_stats:
        _model_call_stats[fm] = {"success": 0, "quota_error": 0, "other_error": 0}

_last_quota_error_time: Optional[datetime] = None
_current_primary_model: str = GEMINI_MODEL
_validated_models: Optional[List[str]] = None


def validate_gemini_models() -> List[str]:
    """Validate configured Gemini models against the API to ensure they exist and support generation."""
    global _validated_models
    if _validated_models is not None:
        return _validated_models
        
    configure_gemini()
    
    available_models = []
    try:
        # Fetch all available models from Gemini
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.replace('models/', '')
                available_models.append(name)
    except Exception as e:
        logger.warning(f"[AI] Failed to fetch model list from Gemini API: {e}. Blindly accepting configured models.")
        _validated_models = [GEMINI_MODEL] + [m for m in GEMINI_FALLBACK_MODELS if m != GEMINI_MODEL]
        return _validated_models
        
    configured = [GEMINI_MODEL] + [m for m in GEMINI_FALLBACK_MODELS if m != GEMINI_MODEL]
    valid = []
    
    for model_name in configured:
        if model_name in available_models or f"models/{model_name}" in available_models:
            valid.append(model_name)
            logger.info(f"[AI] Validation passed for model: {model_name}")
        else:
            logger.warning(f"[AI] Validation failed: Model '{model_name}' is not available (e.g. preview not released) or doesn't support generation. Skipping securely.")
            
    if not valid:
        logger.error("[AI] No configured Gemini models are valid! Falling back to base GEMINI_MODEL as a last resort.")
        valid = [GEMINI_MODEL]
        
    _validated_models = valid
    return valid


def get_queue_status() -> Dict:
    """Return current telemetry and fallback status for Telegram /queue command."""
    return {
        "primary_model": GEMINI_MODEL,
        "current_active_model": _current_primary_model,
        "fallback_models": GEMINI_FALLBACK_MODELS,
        "validated_models": _validated_models if _validated_models is not None else [],
        "stats": _model_call_stats,
        "last_quota_error": _last_quota_error_time.isoformat() if _last_quota_error_time else None
    }


def _generate_with_fallback(prompt: str) -> str:
    """Attempt generation with primary model, fallback on quota errors."""
    global _current_primary_model, _last_quota_error_time
    
    # Always try the primary model first, then the fallbacks, but only use validated ones
    models_to_try = validate_gemini_models()
    
    last_error = None
    
    for model_name in models_to_try:
        try:
            model = get_gemini_model(model_name)
            
            if model_name == GEMINI_MODEL:
                logger.debug(f"[AI] AI Generation utilizing primary model: {model_name}")
            else:
                logger.info(f"[AI] Attempting fallback generation with model: {model_name}")
                
            response = model.generate_content(prompt)
            
            # Record success
            _model_call_stats[model_name]["success"] += 1
            if _current_primary_model != model_name:
                logger.info(f"[AI] Fallback successful. Model {model_name} generated the response.")
                _current_primary_model = model_name
                
            return response.text.strip()
            
        except google_exceptions.ResourceExhausted as e:
            logger.warning(f"[AI] Quota exceeded for model {model_name}. Attempting fallback...")
            _model_call_stats[model_name]["quota_error"] += 1
            _last_quota_error_time = datetime.now()
            last_error = e
            continue
            
        except Exception as e:
            logger.error(f"[AI] Unexpected error generating with {model_name}: {e}")
            _model_call_stats[model_name]["other_error"] += 1
            raise e
            
    logger.error("[AI] All Gemini fallback models exhausted. Generation failed.")
    if last_error:
        raise last_error
    raise RuntimeError("Generation failed across all configured models.")



# =============================================================================
# Time Range Labels
# =============================================================================

TIME_LABELS = {
    "hour": "in the last hour",
    "day": "today",
    "week": "this week",
    "month": "this month",
    "year": "this year",
    "all": "of all time",
}


# =============================================================================
# Post Formatting
# =============================================================================

def _format_post_for_llm(post: PostData, index: int = 1) -> str:
    """Format a single post with its comments for LLM processing."""
    lines = []
    lines.append(f"[Post {index}]")
    lines.append(f"Title: {post['title']}")
    lines.append(f"Score: {post['score']} upvotes | {post['num_comments']} comments")
    
    if post.get('selftext'):
        text = post['selftext'][:1200] if len(post['selftext']) > 1200 else post['selftext']
        lines.append(f"Body: {text}")
    
    comments = post.get('comments', [])
    if comments:
        lines.append("Top comments:")
        for i, c in enumerate(comments[:4], 1):
            body = c.get('body', '')[:250]
            score = c.get('score', 0)
            lines.append(f"  - ({score} pts) {body}")
    
    return "\n".join(lines)


def format_posts_for_prompt(posts: list[PostData]) -> str:
    """Format all posts into a single string for prompt injection."""
    if not posts:
        return "[No posts available]"
    
    formatted = []
    for i, post in enumerate(posts, 1):
        formatted.append(_format_post_for_llm(post, i))
        formatted.append("")
    
    return "\n".join(formatted)


# =============================================================================
# UNIVERSAL Topic Mismatch Detection 
# =============================================================================

# Comprehensive topic indicators for all domains
TOPIC_INDICATORS: Dict[str, List[str]] = {
    "ai": [
        "ai", "gpt", "chatgpt", "llm", "model", "machine learning", "neural",
        "openai", "claude", "gemini", "anthropic", "training", "fine-tuning",
        "prompt", "transformer", "deep learning", "inference", "llama"
    ],
    "tech": [
        "apple", "google", "microsoft", "iphone", "android", "cpu", "gpu",
        "chip", "nvidia", "intel", "amd", "smartphone", "laptop", "hardware",
        "software", "app", "device", "gadget"
    ],
    "programming": [
        "code", "python", "javascript", "developer", "programming", "bug",
        "api", "github", "framework", "library", "react", "node", "database",
        "frontend", "backend", "deploy", "docker", "rust", "typescript"
    ],
    "sports": [
        "game", "player", "team", "score", "win", "match", "championship",
        "league", "coach", "season", "nba", "nfl", "football", "soccer",
        "basketball", "goal", "touchdown", "playoff", "draft"
    ],
    "politics": [
        "election", "vote", "president", "congress", "democrat", "republican",
        "government", "political", "senate", "law", "policy", "trump", "biden",
        "parliament", "party", "legislation", "supreme court"
    ],
    "gaming": [
        "game", "playstation", "xbox", "nintendo", "steam", "gamer", "fps",
        "rpg", "multiplayer", "dlc", "mod", "esports", "console", "pc gaming",
        "ps5", "switch", "controller", "campaign", "gameplay"
    ],
    "crypto": [
        "bitcoin", "ethereum", "crypto", "blockchain", "nft", "defi", "token",
        "coin", "wallet", "mining", "btc", "eth", "solana", "altcoin",
        "exchange", "binance", "coinbase"
    ],
    "science": [
        "research", "study", "scientist", "discovery", "experiment", "nasa",
        "space", "physics", "biology", "chemistry", "quantum", "climate",
        "astronomy", "telescope", "planet", "rocket", "spacex"
    ],
}


def detect_topic_mismatch(expected_topic: str, posts: list[PostData]) -> tuple[bool, str, float]:
    """
    Check if fetched posts seem off-topic from what user asked for.
    Returns (is_mismatch, detected_actual_topic, confidence).
    
    Works for ALL topics, not just a few.
    """
    if not posts:
        return False, "", 0.0
    
    # Combine all titles and bodies for analysis
    texts = []
    for p in posts:
        texts.append(p.get('title', '').lower())
        texts.append((p.get('selftext', '') or '')[:500].lower())
    
    all_text = " ".join(texts)
    
    # Count indicators for each topic
    scores: Dict[str, int] = {}
    for topic, keywords in TOPIC_INDICATORS.items():
        score = sum(1 for kw in keywords if kw in all_text)
        if score > 0:
            scores[topic] = score
    
    # Find the most likely actual topic
    if not scores:
        return False, "", 0.0
    
    detected_topic = max(scores, key=scores.get)
    detected_score = scores[detected_topic]
    expected_score = scores.get(expected_topic, 0)
    
    # Calculate confidence of mismatch
    total_score = sum(scores.values())
    if total_score == 0:
        return False, "", 0.0
    
    detected_ratio = detected_score / total_score
    expected_ratio = expected_score / total_score
    
    # Strong mismatch if detected topic dominates and expected topic is weak
    if detected_topic != expected_topic:
        if detected_ratio >= 0.5 and expected_ratio < 0.2:
            confidence = detected_ratio - expected_ratio
            logger.warning(
                "[AI] Topic mismatch detected: expected=%s, detected=%s, "
                "confidence=%.2f, expected_ratio=%.2f, detected_ratio=%.2f",
                expected_topic, detected_topic, confidence,
                expected_ratio, detected_ratio
            )
            return True, detected_topic, confidence
    
    logger.debug(
        "[AI] No mismatch: expected=%s, detected=%s, "
        "expected_ratio=%.2f, detected_ratio=%.2f",
        expected_topic, detected_topic,
        expected_ratio, detected_ratio
    )
    return False, "", 0.0


def analyze_post_relevance(posts: list[PostData], user_question: str, topic: str) -> str:
    """
    Provide a brief analysis of what the posts are actually about.
    Useful when there might be a mismatch.
    """
    if not posts:
        return "No posts to analyze."
    
    # Get the main themes from titles
    titles = [p.get('title', '') for p in posts[:5]]
    
    return f"The posts fetched appear to discuss: " + "; ".join(t[:60] for t in titles if t)


# =============================================================================
# Intent-Specific Prompt Templates
# =============================================================================

def get_prompt_for_intent(
    intent: str,
    user_question: str,
    topic: str,
    time_range: str,
    formatted_posts: str,
    num_posts: int,
    detected_entities: list[str] = None,
    conversation_context: str = "",
    is_global_search: bool = False
) -> str:
    """Generate the appropriate prompt based on user intent via the prompt registry."""
    from .prompts import BASE_SYSTEM_PROMPT, INTENT_TEMPLATES
    
    time_label = TIME_LABELS.get(time_range, time_range)
    entities_str = ", ".join(detected_entities) if detected_entities else "none specifically"
    
    global_note = ""
    if is_global_search:
        global_note = "\n[NOTE]: I couldn't find a dedicated subreddit for this, so I searched Reddit globally to find these posts. Please mention this briefly in your response.\n"

    # Assemble base context
    base_context = f"""{BASE_SYSTEM_PROMPT}

=== USER'S QUESTION ===
{user_question}

=== CONTEXT ===
Topic: {topic}
Time range: {time_label}
Entities mentioned: {entities_str}
Number of posts: {num_posts}
{f"Previous context: {conversation_context}" if conversation_context else ""}{global_note}

=== REDDIT DATA ===
{formatted_posts}
"""
    
    # Get specific intent template, default to summarize
    intent_template = INTENT_TEMPLATES.get(intent, INTENT_TEMPLATES["summarize"])
    
    return f"{base_context}\n{intent_template}"


def get_followup_prompt(
    user_message: str,
    topic: str,
    time_range: str,
    formatted_posts: str,
    num_posts: int,
    previous_question: str,
    previous_topic: str,
    follow_type: str
) -> str:
    """
    Generate prompt for follow-up questions.
    """
    time_label = TIME_LABELS.get(time_range, time_range)
    
    adjustment_note = ""
    if follow_type == "time_change":
        adjustment_note = f"I've adjusted the time range to {time_label} as you requested."
    elif follow_type == "topic_correction":
        if topic != previous_topic:
            adjustment_note = f"Understood - switching from {previous_topic} to {topic}."
        else:
            adjustment_note = "Understood - refocusing the query."
    
    return f"""You are Reddit Digest handling a FOLLOW-UP message.

=== PREVIOUS QUESTION ===
{previous_question}
(Topic: {previous_topic})

=== USER'S FOLLOW-UP ===
{user_message}

=== ADJUSTMENT ===
{adjustment_note}

=== CURRENT CONTEXT ===
Topic: {topic}
Time range: {time_label}
Posts: {num_posts}

=== REDDIT DATA ===
{formatted_posts}

=== INSTRUCTIONS ===
1. Acknowledge the adjustment briefly (one line max)
2. Then provide the updated information as requested
3. Keep the same helpful, direct style
4. Focus on what's NEW or DIFFERENT from before if relevant

Respond naturally:"""


def get_mismatch_response(
    expected_topic: str, 
    actual_topic: str, 
    user_question: str,
    posts: list[PostData],
    time_range: str
) -> str:
    """Generate response when fetched posts don't match expected topic."""
    time_label = TIME_LABELS.get(time_range, time_range)
    
    # Show what posts are actually about
    actual_titles = [p.get('title', '')[:50] for p in posts[:3]]
    titles_preview = "; ".join(actual_titles)
    
    return f"""⚠️ **Heads up**: You asked about **{expected_topic}**, but the posts I found {time_label} seem to be mainly about **{actual_topic}**.

**What the posts are about:** {titles_preview}...

This can happen if:
- The {expected_topic} subreddits are quiet right now
- There's overlap or mismapping in subreddits

**What would you like to do?**
1. I can summarize what I found (it's mostly about {actual_topic})
2. You can try: "show me {expected_topic} from this week" to broaden the search
3. You can correct me: "I meant [specific thing]"

Just let me know!"""


def get_no_posts_response(topic: str, time_range: str, detected_entities: list[str] = None) -> str:
    """Generate a helpful response when no/few posts are found."""
    time_label = TIME_LABELS.get(time_range, time_range)
    
    entity_note = ""
    if detected_entities:
        entity_note = f"\n- For {detected_entities[0]} specifically, try searching this week or month"
    
    return f"""I couldn't find enough relevant posts about **{topic}** {time_label}.

This might mean:
- The topic is quiet in this time range
- The subreddits don't have much activity right now

**Try:**
- A longer time range: "this week" or "this month"
- Be more specific: mention a game/model/team/coin by name{entity_note}
- Type `/topics` to see what topics I cover

What else can I help with?"""


# =============================================================================
# Main AI Functions
# =============================================================================

def summarize_single_post(post: PostData) -> str:
    """Generate an AI-powered summary for a single post."""
    post_content = _format_post_for_llm(post, 1)
    
    prompt = f"""Summarize this Reddit post in 2-4 sentences.
Focus on: the main point, notable community reactions, and why it matters.

{post_content}

Be concise and informative."""

    try:
        return _generate_with_fallback(prompt)
    except Exception as e:
        return f"Error summarizing post: {str(e)}"


def generate_response(
    user_question: str,
    posts: list[PostData],
    topic: str,
    time_range: str = "day",
    intent: str = "summarize",
    detected_entities: list[str] = None,
    conversation_context: str = "",
    is_followup: bool = False,
    previous_question: str = "",
    previous_topic: str = "",
    previous_time_range: str = "",
    follow_type: str = "",
    is_global_search: bool = False,
    skip_mismatch_check: bool = False
) -> str:
    """
    Main function to generate AI responses.
    Handles intent-awareness, follow-ups, and topic mismatches.
    """
    # Handle no posts
    if not posts:
        logger.info(
            "[AI] No posts available: topic=%s, query='%s'",
            topic, user_question[:60]
        )
        return get_no_posts_response(topic, time_range, detected_entities)
    
    # Check for topic mismatch
    # SKIPPING if explicit entities were detected or manually skipped. 
    # The NLU registry is highly accurate. If it routed via an entity override (e.g. 'TFT' -> 'TeamfightTactics'), 
    # we shouldn't let the LLM's generic keyword detector second-guess it.
    is_mismatch = False
    actual_topic = ""
    confidence = 0.0
    
    if not detected_entities and not skip_mismatch_check:
        is_mismatch, actual_topic, confidence = detect_topic_mismatch(topic, posts)
        
    if is_mismatch and confidence > 0.3:
        logger.warning(
            "[AI] Returning mismatch response: expected=%s, actual=%s, "
            "confidence=%.2f, query='%s'",
            topic, actual_topic, confidence, user_question[:60]
        )
        return get_mismatch_response(topic, actual_topic, user_question, posts, time_range)
    
    # Format posts
    formatted_posts = format_posts_for_prompt(posts)
    num_posts = len(posts)
    
    # Choose prompt based on context
    if is_followup and previous_question and follow_type:
        prompt = get_followup_prompt(
            user_message=user_question,
            topic=topic,
            time_range=time_range,
            formatted_posts=formatted_posts,
            num_posts=num_posts,
            previous_question=previous_question,
            previous_topic=previous_topic,
            follow_type=follow_type
        )
    else:
        prompt = get_prompt_for_intent(
            intent=intent,
            user_question=user_question,
            topic=topic,
            time_range=time_range,
            formatted_posts=formatted_posts,
            num_posts=num_posts,
            detected_entities=detected_entities,
            conversation_context=conversation_context,
            is_global_search=is_global_search
        )
    
    # Generate response
    try:
        logger.info(
            "[AI] Generating response: topic=%s, intent=%s, "
            "posts=%d, is_followup=%s, query='%s'",
            topic, intent, len(posts), is_followup,
            user_question[:60]
        )
        return _generate_with_fallback(prompt)
    except Exception as e:
        logger.error(
            "[AI] Error generating response: %s, query='%s'",
            e, user_question[:60]
        )
        
        # Build a structured debug validation fallback
        retrieval_mode = "Passive Listing Mode"
        if is_global_search:
            retrieval_mode = "Global Search"
        elif detected_entities or intent in ["compare", "shopping", "drama", "help"]:
            retrieval_mode = "Active Subreddit Search"
            
        subreddits = list(set([p.get("subreddit", "unknown") for p in posts]))
        
        fallback = [
            "⚠️ **LLM Generation Failed (Quota / Rate Limit)** ⚠️",
            "Returning Retrieval Validation Debug Output:",
            "---",
            f"**Detected Intent:** `{intent}`",
            f"**Detected Entities:** `{detected_entities}`",
            f"**Retrieval Mode:** `{retrieval_mode}`",
            f"**Targeted Subreddits:** `{subreddits}`",
            f"**Total Posts Fetched:** `{len(posts)}`",
            "---",
            "**Top Fetched Posts:**"
        ]
        
        for i, p in enumerate(posts[:5]):
            title = p.get('title', 'Unknown Title')
            sub = p.get('subreddit', 'unknown')
            fallback.append(f"{i+1}. [r/{sub}] {title}")
            
        fallback.append("\n*(This debug mode was triggered instead of a hard crash so you can validate Stage 6 routing without LLM quotas blocking you.)*")
        
        return "\n".join(fallback)


# =============================================================================
# Legacy Compatibility
# =============================================================================

def summarize_topic(posts: list[PostData], topic: str, time_range: str = "day", language: str = "en") -> str:
    """Legacy function - redirects to generate_response."""
    return generate_response(
        user_question=f"What's happening in {topic}?",
        posts=posts,
        topic=topic,
        time_range=time_range,
        intent="summarize"
    )


def generate_chat_response(
    user_query: str,
    posts: Optional[list[PostData]] = None,
    topic: str = "",
    context: str = "",
    language: str = "en"
) -> str:
    """Legacy function - redirects to generate_response."""
    return generate_response(
        user_question=user_query,
        posts=posts or [],
        topic=topic,
        time_range="day",
        intent="summarize",
        conversation_context=context
    )
