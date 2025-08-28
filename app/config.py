import os
from dotenv import load_dotenv
from praw import reddit
# Load variables from .env if present (development convenience)
load_dotenv()

APP_NAME = "AI Reddit Summarizer"
APP_VERSION = "0.1.0"
DEFAULT_SUBREDDIT = "machinelearning"
AI_SUBREDDITS = ["MachineLearning", "artificial", "OpenAI", "LocalLLaMA", "deeplearning", "ChatGPT"]
TOP_LIMIT = int(os.getenv("TOP_LIMIT") or "5")


# Secrets / credentials (required)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AI-Reddit-Summarizer/0.1 by Competitive-Drama-71")

REQUIRED = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]
MISSING = [k for k in REQUIRED if not globals().get(k)]
if MISSING:
    raise RuntimeError(f"Missing required env vars: {MISSING}. Put them in .env")
