# app/user_preferences.py
# User preferences storage and management

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

# Default preferences file location
PREFERENCES_DIR = Path.home() / ".reddit_digest"
PREFERENCES_FILE = PREFERENCES_DIR / "preferences.json"


@dataclass
class UserPreferences:
    """User preferences for Reddit Digest."""
    
    # Display preferences
    language: str = "en"  # English only
    
    # Content preferences
    favorite_topics: list[str] = field(default_factory=lambda: ["tech", "ai"])
    favorite_subreddits: list[str] = field(default_factory=list)
    
    # Fetch preferences
    default_limit: int = 5
    default_time_range: str = "day"
    min_score: int = 10
    
    # Automation preferences
    weekly_digest_enabled: bool = False
    weekly_digest_day: str = "sunday"  # Day of week for weekly digest
    weekly_digest_topics: list[str] = field(default_factory=lambda: ["tech", "ai"])
    
    # Cache preferences (for cost reduction)
    cache_enabled: bool = True
    cache_duration_hours: int = 1  # How long to cache results
    
    def to_dict(self) -> dict:
        """Convert preferences to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserPreferences":
        """Create preferences from dictionary."""
        # Only use known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


def ensure_preferences_dir():
    """Ensure the preferences directory exists."""
    PREFERENCES_DIR.mkdir(parents=True, exist_ok=True)


def load_preferences() -> UserPreferences:
    """Load user preferences from file, or return defaults."""
    try:
        if PREFERENCES_FILE.exists():
            with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return UserPreferences.from_dict(data)
    except Exception as e:
        print(f"Warning: Could not load preferences: {e}")
    
    return UserPreferences()


def save_preferences(prefs: UserPreferences) -> bool:
    """Save user preferences to file."""
    try:
        ensure_preferences_dir()
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(prefs.to_dict(), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving preferences: {e}")
        return False


def update_preference(key: str, value) -> UserPreferences:
    """Update a single preference and save."""
    prefs = load_preferences()
    if hasattr(prefs, key):
        setattr(prefs, key, value)
        save_preferences(prefs)
    return prefs


def add_favorite_topic(topic: str) -> UserPreferences:
    """Add a topic to favorites."""
    prefs = load_preferences()
    if topic not in prefs.favorite_topics:
        prefs.favorite_topics.append(topic)
        save_preferences(prefs)
    return prefs


def remove_favorite_topic(topic: str) -> UserPreferences:
    """Remove a topic from favorites."""
    prefs = load_preferences()
    if topic in prefs.favorite_topics:
        prefs.favorite_topics.remove(topic)
        save_preferences(prefs)
    return prefs


def add_favorite_subreddit(subreddit: str) -> UserPreferences:
    """Add a subreddit to favorites."""
    prefs = load_preferences()
    if subreddit not in prefs.favorite_subreddits:
        prefs.favorite_subreddits.append(subreddit)
        save_preferences(prefs)
    return prefs


def enable_weekly_digest(topics: Optional[list[str]] = None, day: str = "sunday") -> UserPreferences:
    """Enable weekly digest automation."""
    prefs = load_preferences()
    prefs.weekly_digest_enabled = True
    prefs.weekly_digest_day = day
    if topics:
        prefs.weekly_digest_topics = topics
    save_preferences(prefs)
    return prefs


def disable_weekly_digest() -> UserPreferences:
    """Disable weekly digest automation."""
    prefs = load_preferences()
    prefs.weekly_digest_enabled = False
    save_preferences(prefs)
    return prefs


def get_preferences_summary(language: str = "he") -> str:
    """Get a formatted summary of current preferences."""
    prefs = load_preferences()
    
    if language == "he":
        digest_status = "מופעל ✅" if prefs.weekly_digest_enabled else "מכובה ❌"
        cache_status = "מופעל ✅" if prefs.cache_enabled else "מכובה ❌"
        
        return f"""
⚙️ **ההגדרות שלך**

**שפה:** {"עברית 🇮🇱" if prefs.language == "he" else "English 🇺🇸"}

**נושאים מועדפים:** {', '.join(prefs.favorite_topics) or 'לא הוגדרו'}

**סאב-רדיטים מועדפים:** {', '.join(prefs.favorite_subreddits) or 'לא הוגדרו'}

**הגדרות ברירת מחדל:**
• מספר פוסטים: {prefs.default_limit}
• טווח זמן: {prefs.default_time_range}
• ציון מינימלי: {prefs.min_score}

**דייג'סט שבועי:** {digest_status}
{f'• יום: {prefs.weekly_digest_day}' if prefs.weekly_digest_enabled else ''}
{f'• נושאים: {", ".join(prefs.weekly_digest_topics)}' if prefs.weekly_digest_enabled else ''}

**מטמון (חיסכון בעלויות):** {cache_status}
{f'• משך: {prefs.cache_duration_hours} שעות' if prefs.cache_enabled else ''}
"""
    else:
        digest_status = "Enabled ✅" if prefs.weekly_digest_enabled else "Disabled ❌"
        cache_status = "Enabled ✅" if prefs.cache_enabled else "Disabled ❌"
        
        return f"""
⚙️ **Your Settings**

**Language:** {"Hebrew 🇮🇱" if prefs.language == "he" else "English 🇺🇸"}

**Favorite Topics:** {', '.join(prefs.favorite_topics) or 'None set'}

**Favorite Subreddits:** {', '.join(prefs.favorite_subreddits) or 'None set'}

**Default Settings:**
• Number of posts: {prefs.default_limit}
• Time range: {prefs.default_time_range}
• Minimum score: {prefs.min_score}

**Weekly Digest:** {digest_status}
{f'• Day: {prefs.weekly_digest_day}' if prefs.weekly_digest_enabled else ''}
{f'• Topics: {", ".join(prefs.weekly_digest_topics)}' if prefs.weekly_digest_enabled else ''}

**Cache (Cost Saving):** {cache_status}
{f'• Duration: {prefs.cache_duration_hours} hours' if prefs.cache_enabled else ''}
"""
