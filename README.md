# Reddit Digest - AI-Powered Reddit Summarizer Bot

**Currently offline:** The bot was previously deployed on Render, but the hosted service is no longer running. The [previous Telegram bot](https://t.me/RedditFetch_bot) is a historical reference, not an active demo. To use the project, run your own instance with the instructions below.

Reddit Digest is an AI-powered Telegram bot that helps users stay updated on topics they care about by collecting Reddit discussions, extracting relevant posts and comments, and generating concise AI summaries.

The project was built as a personal software engineering project focused on real-world API integration, AI summarization, user preferences, scheduling, logging, and retrieval-quality improvements.

## Run Locally

### 1. Clone the Main Branch and Install Dependencies

Use Python 3.10 or newer, Git, and an internet connection. Run the commands from the repository root. The `main` branch includes the merged `upgrade` changes; no separate feature-branch checkout is needed for these instructions.

```sh
git clone --branch main https://github.com/nitzangal007/AI-Reddit-Digest.git
cd AI-Reddit-Digest
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

On macOS or Linux, use `python3` instead of `python` when creating the virtual environment, then:

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

For an existing checkout, use `git switch main` and `git pull --ff-only origin main` before installing dependencies. Copy `.env.example` only when `.env` does not already exist, to preserve your credentials.

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` instead of `python` in subsequent commands. Activation is a convenience; it is not required.

### 2. Configure Credentials

Edit the local `.env` file and replace the placeholder values:

| Variable | Required for | Purpose |
|----------|--------------|---------|
| `REDDIT_CLIENT_ID` | All modes, including CLI help | Reddit API client ID |
| `REDDIT_CLIENT_SECRET` | All modes, including CLI help | Reddit API client secret |
| `REDDIT_USER_AGENT` | Recommended for all Reddit requests | An identifying string such as `RedditDigest/0.2 by YourUsername` |
| `GEMINI_API_KEY` | AI summaries and Telegram startup | Google Gemini API key |
| `TELEGRAM_BOT_TOKEN` | Telegram mode | Token for your own bot, obtained through Telegram's `@BotFather` |
| `GEMINI_MODEL` | Optional | Model ID available to your Gemini account; the configured default is in `app/config.py` |
| `APP_DATA_DIR` | Optional locally | Directory for Telegram SQLite state and rotating application logs |

Reddit credentials require an API application and permitted API access. The application setup page is [Reddit apps](https://www.reddit.com/prefs/apps). Obtain a Gemini key from [Google AI Studio](https://aistudio.google.com/app/apikey). API access, quotas, model availability, and any provider charges depend on your own accounts.

You must supply your own credentials. `.env` is ignored by Git; keep API keys and bot tokens private.

### 3. Start the Telegram Bot

With the virtual environment active and `.env` configured:

```sh
python -m app.telegram_bot
```

Open the bot associated with **your token** in Telegram, send `/start`, and complete onboarding. Use `/settings` to configure topics, subreddits, and delivery preferences, then `/digest` to request a digest. You can also send a question such as `What happened this week in AI?`.

The application uses long polling, so local operation does not require a public URL or webhook server. Run only one polling instance per bot token. Keep the process running and the computer awake for scheduled delivery; press `Ctrl+C` to stop it. Digest times use the machine's local timezone, and missed deliveries are not replayed while the process is stopped.

### 4. Use the CLI Instead

CLI chat and AI queries use the same Reddit and Gemini credentials but do not require a Telegram token:

```sh
python -m app --help
python -m app --chat
python -m app --query "What happened this week in AI?"
```

For the legacy post-fetching mode:

```sh
python -m app --subreddit machinelearning --sort top --time week --limit 5
```

The CLI also exposes `--digest-now` and `--schedule` for its own configured weekly digests. CLI preferences are separate from Telegram user preferences. Telegram daily and weekly jobs already run inside `python -m app.telegram_bot`; they do not require a separate CLI scheduler.

### Optional Email Delivery

Uncomment and configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `EMAIL_FROM` in `.env` to enable SMTP delivery. The sender uses STARTTLS; the example uses port `587`. Without SMTP credentials, Telegram and CLI use remain available.

In Telegram, use `/set_email` and `/email_digest` to configure and enable email copies. Actual delivery requires valid SMTP credentials and provider access.

### Local Data and Troubleshooting

By default, Telegram preferences are stored in `~/.reddit_digest/telegram_users.db`, and application logs in `~/.reddit_digest/logs/app.log`. `~` means your home directory. `APP_DATA_DIR` overrides these Telegram paths. The JSON cache, CLI preferences, and generated digest files still use `~/.reddit_digest`, independently of that override.

| Symptom | Check |
|---------|-------|
| `Missing required env vars` or startup validation error | Confirm `.env` is in the repository root, placeholders are replaced, and all credentials required for the selected mode are set. |
| Import error or missing JobQueue | Use the virtual environment and reinstall `requirements.txt`, which includes `python-telegram-bot[job-queue]`. |
| Bot does not respond | Check the terminal logs, the bot associated with your token, network access, and whether another instance is polling the same token. |
| Reddit or Gemini request fails | Check API permissions, key validity, quota, and Gemini model availability. Successful startup does not prove external API access. |
| Scheduled digest does not arrive | Keep the process running, check the machine timezone, and review `/settings` and logs. |

### Hosting Files

`render.yaml` describes a Python background worker with `python -m app.telegram_bot` as its start command and a persistent disk for Telegram state. It is configuration for a future deployment, not evidence that a service is currently hosted. On Render, startup requires `APP_DATA_DIR`; the blueprint sets it to `/var/data/reddit_digest`.

The root `Dockerfile` contains an unrelated Tomcat/JSP setup and does not run this Python bot. Use the Python commands above for local operation.

---

## What the Bot Does

Reddit Digest allows users to ask natural-language questions such as:

- “What’s new in AI this week?”
- “Show me trending gaming posts”
- “Summarize the top tech news”
- “What are people saying about Real Madrid?”
- “Give me a digest from my selected subreddits”

The bot fetches relevant Reddit posts and comments, sends them through an AI summarization pipeline, and returns a clear digest directly inside Telegram.

---

## Main Features

### Telegram Bot Interface

The project includes a full Telegram bot experience:

- User onboarding flow with guided setup
- Custom subreddit selection
- Custom topic selection
- Daily and weekly digest preferences
- Manual digest generation with `/digest`
- Interactive settings panel
- Commands for topics, frequency, email delivery, reset, and queue status

### Personalized Reddit Digests

Users can configure what they care about:

- Favorite subreddits
- Favorite topics
- Digest frequency
- Digest time
- Weekly digest day
- Optional email delivery

This makes the bot behave more like a personalized assistant than a one-time summarization script.

### AI-Powered Summarization

The bot uses Google Gemini to summarize Reddit posts and top comments.

The summarization pipeline is designed to:

- Stay grounded in the retrieved Reddit content
- Summarize community discussions clearly
- Separate facts from rumors or speculation
- Adapt the answer structure based on the user’s intent

Supported intent types include:

- General summaries
- News updates
- Comparisons
- Community sentiment
- Drama or controversy summaries
- Product or recommendation discussions

### Reddit Retrieval Pipeline

The bot retrieves Reddit data through the Reddit API using PRAW.

The retrieval layer supports:

- Fetching posts from selected subreddits
- Fetching top comments for additional context
- Searching inside specific subreddits
- Global Reddit search as a fallback
- Filtering low-quality or irrelevant posts
- Expanding the search window when there are not enough results

### Natural Language Understanding

The project includes an NLU layer that parses the user’s message into:

- Topic
- Intent
- Time range
- Mentioned entities
- Target subreddits
- Confidence level

For example, a query like:

```text
What happened this week in AI?
```

can be converted into a structured retrieval request that identifies the topic, time range, and relevant communities.

### Persistent User Preferences

Telegram user preferences are stored persistently with SQLite.

The bot keeps track of:

- Chat ID
- Username
- Selected subreddits
- Selected topics
- Daily or weekly digest settings
- Digest delivery time
- Email address
- Email delivery preference
- Onboarding status

This allows each user to have a personalized experience across sessions.

### Scheduled Automation

The bot supports automatic digest delivery.

Users can receive:

- Daily digests
- Weekly digests
- Manual digests on demand

Scheduled jobs check user preferences and send digests at the configured time.

### Email Digest Support

In addition to Telegram delivery, the bot supports optional email delivery using SMTP.

This adds another notification channel and demonstrates integration with email infrastructure.

### Logging and Observability

The project includes structured logging across important system decisions, including:

- Topic detection
- Entity matching
- Subreddit routing
- Reddit fetching
- Cache hits
- Search broadening
- Topic mismatch detection
- AI generation
- Model fallback behavior

This makes the system easier to debug, monitor, and improve.

### Caching

The project includes a local caching layer to reduce repeated API calls and improve response efficiency.

Cached data is stored with query-based keys and expiration logic.

---

## Tech Stack

| Area | Tools / Technologies |
|------|----------------------|
| Language | Python |
| Bot Framework | python-telegram-bot |
| Reddit API | PRAW |
| AI Model | Google Gemini API |
| Storage | SQLite |
| Scheduling | Telegram JobQueue / schedule |
| Email Delivery | SMTP |
| Configuration | python-dotenv |
| CLI Formatting | Rich |
| Debugging | Python logging |
| Architecture | Modular Python package |

---

## High-Level Architecture

```text
User Message
    |
    v
Telegram Bot
    |
    v
Conversation Handler
    |
    v
NLU Parser
(topic, intent, entities, time range, confidence)
    |
    v
Retrieval Layer
(subreddit routing / Reddit search / global fallback)
    |
    v
Reddit API
(posts + comments)
    |
    v
AI Engine
(prompt construction + Gemini summarization)
    |
    v
Formatted Response
(Telegram / Email)
```

---

## Core Modules

```text
app/
├── telegram_bot.py       # Telegram bot handlers, onboarding, commands, scheduled jobs
├── conversation.py       # Main conversation and retrieval pipeline
├── nlu.py                # Natural-language parsing: topic, intent, entities, time range
├── reddit_client.py      # Reddit API integration and post/comment fetching
├── ai_engine.py          # Gemini integration, prompts, model fallback, grounded responses
├── user_store.py         # SQLite storage for Telegram user preferences
├── email_notifier.py     # Optional email digest delivery
├── scheduler.py          # Scheduled digest generation
├── cache.py              # Local caching layer
├── registry.py           # Entity/topic registry loader
├── prompts.py            # Intent-specific prompt templates
└── formatter.py          # CLI formatting utilities
```

---

## Engineering Highlights

This project demonstrates practical experience with:

- Building a real user-facing Telegram bot with onboarding and settings
- Working with multiple external APIs: Reddit, Telegram, Gemini, and SMTP
- Designing an AI summarization pipeline
- Managing persistent user preferences with SQLite
- Implementing scheduled digest automation
- Handling multiple delivery channels through Telegram and email
- Writing modular Python code across clear responsibility-based modules
- Designing prompt templates for different user intents
- Adding structured logging for debugging and observability
- Building fallback behavior for unreliable API/model workflows
- Improving retrieval quality through entity detection and confidence signals

---

## Retrieval Quality Improvements

One of the main engineering challenges in this project is retrieval quality.

A simple AI summarizer is not enough: if the bot fetches the wrong Reddit posts, the generated summary will also be wrong.

To address this, the project uses a retrieval pipeline that combines:

- Natural-language parsing
- Entity and topic detection
- Subreddit routing
- Reddit search
- Global search fallback
- Safe responses when relevant content cannot be found

```text
User Query
    |
    v
NLU with confidence
    |
    v
Entity / topic routing
    |
    v
Targeted subreddit retrieval
    |
    v
Reddit search fallback
    |
    v
Global search fallback
    |
    v
AI summarization or safe fallback response
```

The goal is to avoid confidently summarizing irrelevant content when the system does not understand the user’s topic.

---

## Example Use Cases

### AI Digest

A user can ask:

```text
What happened this week in AI?
```

The bot retrieves posts from AI-related communities, includes top comments, and summarizes the most important discussions.

### Custom Subreddit Digest

A user can configure specific subreddits and ask for a digest.

The bot prioritizes the user’s selected communities instead of relying only on broad topics.

### Scheduled Weekly Digest

A user can configure a weekly digest and receive automatic summaries at a selected day and time.

### Email Copy

If enabled, the same digest can also be sent by email.

---

## Bot Commands

| Command | Description |
|--------|-------------|
| `/start` | Start onboarding or view current setup |
| `/settings` | View and change preferences |
| `/help` | Show available commands |
| `/digest` | Generate a digest immediately |
| `/set_frequency` | Configure daily or weekly digest frequency |
| `/set_time` | Set digest delivery time |
| `/set_topics` | Change followed topics |
| `/set_subreddits` | Change followed subreddits |
| `/set_email` | Set or clear email address |
| `/email_digest` | Toggle email delivery |
| `/weekly` | Toggle weekly digest |
| `/topics` | Show available topics |
| `/queue` | Show Gemini model and fallback status |
| `/reset` | Clear preferences |

---

## What I Learned

While building this project, I practiced:

- API integration with Reddit, Telegram, Gemini, and SMTP
- Building a product-like bot with onboarding and user settings
- Designing a multi-stage AI pipeline
- Handling user-specific persistent data
- Debugging real application behavior with structured logs
- Thinking about reliability, fallback behavior, and user trust
- Improving code organization in a growing Python project

---

## Future Improvements

Planned improvements include:

- Expanding the entity registry with more aliases and communities
- Improving post ranking after retrieval
- Adding stronger comparison handling for “X vs Y” questions
- Adding more automated tests
- Improving deployment monitoring
- Adding screenshots or a short demo GIF
- Improving the Telegram UI with more inline controls

---

## Project Status

The bot was previously deployed on Render and is currently offline. There is no active hosted demo. Local operation requires your own Reddit and Gemini credentials, plus a Telegram bot token for Telegram mode.

This repository is part of an ongoing personal portfolio project focused on AI, automation, and real-world software engineering.
