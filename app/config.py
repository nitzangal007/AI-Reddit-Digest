import os
from dotenv import load_dotenv
from praw import reddit
# Load variables from .env if present (development convenience)
load_dotenv()

# =============================================================================
# App Configuration
# =============================================================================
APP_NAME = "Reddit Digest"
APP_VERSION = "0.2.0"
DEFAULT_SUBREDDIT = "machinelearning"
TOP_LIMIT = 10  # Default number of top posts to summarize
DEFAULT_COMMENT_LIMIT = 5  # Default number of top comments to fetch per post
MAX_FETCH_POSTS = 100  # Max posts to fetch from Reddit at once
MAX_FETCH_COMMENTS = 20  # Max comments to fetch per post
OVER_FETCH_FACTOR = 5  # Fetch this many times the TOP_LIMIT to allow filtering

# =============================================================================
# Gemini AI Configuration
# =============================================================================
# Accept both GEMINI_API_KEY and OPENAI_API_KEY (in case user named it differently)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  # Stable base model
_fallback_models_str = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash-lite,gemini-2.5-pro,gemini-3-flash-preview,gemini-3.1-flash-lite-preview,gemini-3.1-pro-preview")
GEMINI_FALLBACK_MODELS = [m.strip() for m in _fallback_models_str.split(",") if m.strip()]

# =============================================================================
# Telegram Bot Configuration
# =============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# =============================================================================
# Topic to Subreddit Mapping
# =============================================================================
# Topic → Subreddit mapping (loaded from external registry)
from .registry import TOPIC_SUBREDDIT_MAP

# Legacy compatibility
AI_SUBREDDITS = TOPIC_SUBREDDIT_MAP.get("ai", [])


#Summary configuration
STOPWORDS={
        "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours",
        "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers",
        "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
        "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are",
        "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does",
        "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as",
        "until", "while",  # Removed 'of' from STOPWORDS
        # Add more STOPWORDS as needed
    }




# Secrets / credentials (required)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AI-Reddit-Summarizer/0.1 by Competitive-Drama-71")

REQUIRED = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]
MISSING = [k for k in REQUIRED if not globals().get(k)]
if MISSING:
    raise RuntimeError(f"Missing required env vars: {MISSING}. Put them in .env")
