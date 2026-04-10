import os
from pathlib import Path
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
# App Data Paths
# =============================================================================
APP_DATA_DIR_ENV = os.getenv("APP_DATA_DIR")
APP_DATA_DIR = Path(APP_DATA_DIR_ENV).expanduser() if APP_DATA_DIR_ENV else Path.home() / ".reddit_digest"
APP_LOG_DIR = APP_DATA_DIR / "logs"
SQLITE_DB_FILE = APP_DATA_DIR / "telegram_users.db"

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


def is_running_on_render() -> bool:
    """Return True when the app appears to be running on Render."""
    return bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("RENDER_INSTANCE_ID"))


def validate_runtime_config() -> dict[str, str]:
    """
    Validate the deployment-facing runtime configuration and prepare directories.

    Returns useful resolved paths for startup logging.
    """
    required_runtime = {
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "REDDIT_CLIENT_ID": REDDIT_CLIENT_ID,
        "REDDIT_CLIENT_SECRET": REDDIT_CLIENT_SECRET,
        "GEMINI_API_KEY": GEMINI_API_KEY,
    }
    missing_runtime = [name for name, value in required_runtime.items() if not value]
    if missing_runtime:
        raise RuntimeError(f"Missing required runtime env vars: {missing_runtime}")

    if is_running_on_render() and not APP_DATA_DIR_ENV:
        raise RuntimeError(
            "APP_DATA_DIR must be set when running on Render so SQLite and logs use the persistent disk."
        )

    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        APP_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(APP_LOG_DIR / "app.log", "a", encoding="utf-8"):
            pass
    except OSError as exc:
        raise RuntimeError(f"Unable to initialize APP_DATA_DIR '{APP_DATA_DIR}': {exc}") from exc

    return {
        "app_data_dir": str(APP_DATA_DIR),
        "app_log_dir": str(APP_LOG_DIR),
        "sqlite_db_file": str(SQLITE_DB_FILE),
        "running_on_render": "true" if is_running_on_render() else "false",
        "using_default_app_data_dir": "true" if not APP_DATA_DIR_ENV else "false",
    }
