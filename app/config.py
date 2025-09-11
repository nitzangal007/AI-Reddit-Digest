import os
from dotenv import load_dotenv
from praw import reddit
# Load variables from .env if present (development convenience)
load_dotenv()

# App configuration
APP_NAME = "AI Reddit Summarizer"
APP_VERSION = "0.1.0"
DEFAULT_SUBREDDIT = "machinelearning"
AI_SUBREDDITS = ["MachineLearning", "artificial", "OpenAI", "LocalLLaMA", "deeplearning", "ChatGPT"]
TOP_LIMIT = 5 # Default number of top posts to summarize  # Default minimum score for posts to consider
DEFAULT_COMMENT_LIMIT = 5  # Default number of top comments to fetch per post
MAX_FETCH_POSTS = 100  # Max posts to fetch from Reddit at once
MAX_FETCH_COMMENTS = 20     # Max comments to fetch per post
OVER_FETCH_FACTOR = 5 # Fetch this many times the TOP_LIMIT to allow filtering


# Secrets / credentials (required)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AI-Reddit-Summarizer/0.1 by Competitive-Drama-71")

REQUIRED = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]
MISSING = [k for k in REQUIRED if not globals().get(k)]
if MISSING:
    raise RuntimeError(f"Missing required env vars: {MISSING}. Put them in .env")
