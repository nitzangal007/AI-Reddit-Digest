# app/user_store.py
# Per-user preference storage using SQLite for Telegram bot

import sqlite3
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import threading

# Database file location
DB_DIR = Path.home() / ".reddit_digest"
DB_FILE = DB_DIR / "telegram_users.db"

# Thread-local storage for connections
_local = threading.local()


@dataclass
class TelegramUserPreferences:
    """User preferences for Telegram bot."""
    
    chat_id: int                                    # Telegram chat_id (primary key)
    username: str = ""                              # Optional @username
    email: str = ""                                 # Optional email for notifications
    
    # Subreddit preferences
    subreddits: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=lambda: ["tech", "ai"])
    
    # Interest definition - what "interesting" means to user
    interest_type: str = "top"                      # "top", "controversial", "tutorials", "product_launches"
    
    # Frequency
    daily_digest_enabled: bool = False
    weekly_digest_enabled: bool = False
    digest_hour: int = 9                            # Hour of day (0-23) for digests
    digest_minute: int = 0                          # Minute of hour (0-59) for digests
    weekly_digest_day: str = "sunday"
    
    # Email delivery
    email_digest_enabled: bool = False              # Send digest copies to email
    
    # Onboarding state
    onboarding_complete: bool = False
    onboarding_step: str = ""                       # Current step in onboarding flow
    
    # Settings
    language: str = "en"
    min_score: int = 10
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert lists to JSON strings for SQLite
        data['subreddits'] = json.dumps(data['subreddits'])
        data['topics'] = json.dumps(data['topics'])
        # Convert datetime to ISO string
        if data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        if data['updated_at']:
            data['updated_at'] = data['updated_at'].isoformat()
        return data
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "TelegramUserPreferences":
        """Create from database row."""
        data = dict(row)
        # Parse JSON lists
        data['subreddits'] = json.loads(data['subreddits']) if data['subreddits'] else []
        data['topics'] = json.loads(data['topics']) if data['topics'] else []
        # Parse datetime
        if data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data['updated_at']:
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        # Convert int to bool
        data['daily_digest_enabled'] = bool(data['daily_digest_enabled'])
        data['weekly_digest_enabled'] = bool(data['weekly_digest_enabled'])
        data['onboarding_complete'] = bool(data['onboarding_complete'])
        data['email_digest_enabled'] = bool(data.get('email_digest_enabled', 0))
        # Ensure digest_minute exists (migration safety)
        data.setdefault('digest_minute', 0)
        return cls(**data)


def ensure_db_dir():
    """Ensure the database directory exists."""
    DB_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Get a thread-local database connection."""
    if not hasattr(_local, 'connection') or _local.connection is None:
        ensure_db_dir()
        _local.connection = sqlite3.connect(str(DB_FILE), check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row
        _init_db(_local.connection)
    return _local.connection


def _init_db(conn: sqlite3.Connection):
    """Initialize database schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            email TEXT DEFAULT '',
            subreddits TEXT DEFAULT '[]',
            topics TEXT DEFAULT '["tech", "ai"]',
            interest_type TEXT DEFAULT 'top',
            daily_digest_enabled INTEGER DEFAULT 0,
            weekly_digest_enabled INTEGER DEFAULT 0,
            digest_hour INTEGER DEFAULT 9,
            digest_minute INTEGER DEFAULT 0,
            weekly_digest_day TEXT DEFAULT 'sunday',
            email_digest_enabled INTEGER DEFAULT 0,
            onboarding_complete INTEGER DEFAULT 0,
            onboarding_step TEXT DEFAULT '',
            language TEXT DEFAULT 'en',
            min_score INTEGER DEFAULT 10,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    # Safe migration for existing databases
    for col, default in [
        ("digest_minute", "0"),
        ("email_digest_enabled", "0"),
    ]:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT {default}")
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()


def get_user(chat_id: int) -> Optional[TelegramUserPreferences]:
    """Get user preferences by chat_id."""
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if row:
        return TelegramUserPreferences.from_row(row)
    return None


def create_user(chat_id: int, username: str = "") -> TelegramUserPreferences:
    """Create a new user with default preferences."""
    now = datetime.now()
    user = TelegramUserPreferences(
        chat_id=chat_id,
        username=username,
        created_at=now,
        updated_at=now
    )
    
    conn = get_connection()
    data = user.to_dict()
    
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?' for _ in data])
    values = list(data.values())
    
    conn.execute(f"INSERT INTO users ({columns}) VALUES ({placeholders})", values)
    conn.commit()
    
    return user


def update_user(prefs: TelegramUserPreferences) -> bool:
    """Update user preferences."""
    prefs.updated_at = datetime.now()
    data = prefs.to_dict()
    
    # Build UPDATE query
    set_clause = ', '.join([f"{k} = ?" for k in data.keys() if k != 'chat_id'])
    values = [v for k, v in data.items() if k != 'chat_id']
    values.append(prefs.chat_id)
    
    conn = get_connection()
    conn.execute(f"UPDATE users SET {set_clause} WHERE chat_id = ?", values)
    conn.commit()
    
    return True


def get_or_create_user(chat_id: int, username: str = "") -> TelegramUserPreferences:
    """Get existing user or create new one."""
    user = get_user(chat_id)
    if user is None:
        user = create_user(chat_id, username)
    return user


def delete_user(chat_id: int) -> bool:
    """Delete a user's preferences (for /reset)."""
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
    conn.commit()
    return True


def get_users_for_daily_digest(hour: int, minute: int) -> List[TelegramUserPreferences]:
    """Get all users who need daily digest at the specified hour and minute."""
    conn = get_connection()
    cursor = conn.execute("""
        SELECT * FROM users 
        WHERE daily_digest_enabled = 1 
        AND digest_hour = ?
        AND digest_minute = ?
        AND onboarding_complete = 1
    """, (hour, minute))
    
    return [TelegramUserPreferences.from_row(row) for row in cursor.fetchall()]


def get_users_for_weekly_digest(day: str, hour: int, minute: int) -> List[TelegramUserPreferences]:
    """Get all users who need weekly digest on the specified day, hour, and minute."""
    conn = get_connection()
    cursor = conn.execute("""
        SELECT * FROM users 
        WHERE weekly_digest_enabled = 1 
        AND weekly_digest_day = ?
        AND digest_hour = ?
        AND digest_minute = ?
        AND onboarding_complete = 1
    """, (day.lower(), hour, minute))
    
    return [TelegramUserPreferences.from_row(row) for row in cursor.fetchall()]


def get_all_subscribed_users() -> List[TelegramUserPreferences]:
    """Get all users with any digest enabled."""
    conn = get_connection()
    cursor = conn.execute("""
        SELECT * FROM users 
        WHERE (daily_digest_enabled = 1 OR weekly_digest_enabled = 1)
        AND onboarding_complete = 1
    """)
    
    return [TelegramUserPreferences.from_row(row) for row in cursor.fetchall()]


def get_user_preferences_summary(user: TelegramUserPreferences) -> str:
    """Get a formatted summary of user preferences."""
    subreddits = ', '.join(user.subreddits) if user.subreddits else 'None set'
    topics = ', '.join(user.topics) if user.topics else 'None set'
    
    daily_status = "✅ Enabled" if user.daily_digest_enabled else "❌ Disabled"
    weekly_status = "✅ Enabled" if user.weekly_digest_enabled else "❌ Disabled"
    email_delivery = "✅ Enabled" if user.email_digest_enabled else "❌ Disabled"
    email_addr = user.email if user.email else "Not set"
    digest_time = f"{user.digest_hour:02d}:{user.digest_minute:02d}"
    
    return f"""⚙️ **Your Settings**

**Subreddits:** {subreddits}
**Topics:** {topics}
**Interest Type:** {user.interest_type}

**Notifications:**
• Daily Digest: {daily_status}
• Weekly Digest: {weekly_status}
{f'• Weekly Day: {user.weekly_digest_day.capitalize()}' + chr(10) if user.weekly_digest_enabled else ''}• Digest Time: {digest_time}
• Email: {email_addr}
• Email Delivery: {email_delivery}

**Other:**
• Min Score: {user.min_score}
• Onboarding: {'Complete ✅' if user.onboarding_complete else 'Incomplete'}
"""
