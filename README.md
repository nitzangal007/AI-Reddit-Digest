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

This allows the bot to understand queries like:

```text
“What happened this week in AI?”
