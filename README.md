## Project Status & MVP Plan

### Current Status
- ✅ Repository set up with clean git hygiene (`.gitignore`, `.gitattributes`, `LICENSE`).
- ✅ Code packaged under `app/` and runnable via `python -m app`.
- ✅ Reddit client (PRAW) fetches posts by subreddit with `--subreddit/-s` and `--limit/-n`.
- ✅ Placeholder summarizer in place (`summarize.py`, short 140-char summary).
- 🔶 README Quickstart & screenshots: **in progress**.
- 🔶 `.env.example`: **in progress**.
- 🔶 CLI prints the AI-like `Summary:` line for each post: **in progress**.
- ⏳ Requirements trimming to core MVP (praw, dotenv, rich).
- ⏳ Tests / CI: not started.

### MVP v0.1 — Scope & Success Criteria
**Goal:** a minimal, working CLI that fetches subreddit posts and prints a short AI-like summary per post.

**Must-haves**
- Fetch top posts from a given subreddit (default: `askreddit`) with a configurable limit.
- For each post, print: **Title**, **Summary** (<= 140 chars, placeholder), and **URL**.
- Graceful handling of empty bodies or rate limits (fallback to title, simple retries or message).
- Run via:  
  ```bash
  python -m app -s <subreddit> -n <limit>

## Quickstart

### 1) Requirements
- Python 3.10+ recommended
- A Reddit application (to obtain `client_id`, `client_secret`, `user_agent`)

### 2) Setup
```bash
# clone & enter
git clone https://github.com/<your-user>/<your-repo>.git
cd <your-repo>

# create & activate a virtual env
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# install dependencies
pip install -r requirements.txt

