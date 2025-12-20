# Reddit Digest 🤖

**Stay updated on what matters to you without scrolling forever.**

Reddit Digest is an AI-powered assistant that tracks your favorite topics and delivers intelligent, concise summaries of the most interesting current discussions.

---

## ✨ Features

- **💬 Natural Chat Interface**: Just ask "What happened in AI this week?"
- **🧠 Smart AI Summaries**: Powered by Google Gemini to analyze and summarize content.
- **⚡ Topics & Subreddits**: Automatically maps topics (Tech, Sports, Politics) to relevant communities.
- **📅 Weekly Digest**: Schedule automated weekly updates for your favorite topics.
- **🚀 English Only**: Clean, professional interface optimized for all terminals.

---

## 🚀 Quick Start

### 1. Install
```bash
git clone https://github.com/your-username/AI-Reddit-Summerizer.git
cd AI-Reddit-Summerizer
python -m venv .venv
# Activate: Windows: .\.venv\Scripts\activate | Mac: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
Create a `.env` file with your keys:
```env
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=RedditDigest/1.0
GEMINI_API_KEY=your_gemini_key  # Get free key from Google AI Studio
GEMINI_MODEL=gemini-pro
```

### 3. Run
```bash
python -m app --chat
```

---

## � Example Prompts

- **"What's trending in tech today?"**
- **"Summarize the top AI news from this week"**
- **"Show me the most interesting sports discussions"**
- **"What are people saying about the new iPhone?"**

---

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `/topics` | See supported topics |
| `/weekly on` | Enable weekly digest |
| `/settings` | View preferences |
| `/quit` | Exit |

---

**License**: MIT
