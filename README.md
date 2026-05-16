# Reddit Digest — AI-Powered Reddit Summarizer Bot

[Try the live Telegram bot](https://t.me/RedditFetch_bot)

Reddit Digest is an AI-powered Telegram bot that helps users stay updated on topics they care about by collecting Reddit discussions, extracting relevant posts and comments, and generating concise AI summaries.

The project was built as a personal software engineering project focused on real-world API integration, AI summarization, user preferences, scheduling, logging, and retrieval-quality improvements.

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

The bot is deployed and usable through Telegram.

This repository is part of an ongoing personal portfolio project focused on AI, automation, and real-world software engineering.
