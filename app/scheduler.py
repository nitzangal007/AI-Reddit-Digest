# app/scheduler.py
# Weekly digest automation scheduler

import schedule
import time
import threading
from datetime import datetime
from typing import Callable, Optional
from pathlib import Path

from .user_preferences import load_preferences
from .conversation import ConversationHandler
from .formatter import console


# Log file for scheduled runs
LOG_DIR = Path.home() / ".reddit_digest" / "logs"


def ensure_log_dir():
    """Ensure the log directory exists."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_digest(content: str, topic: str):
    """Log a digest to file."""
    ensure_log_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"digest_{topic}_{timestamp}.md"
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"# Weekly Digest - {topic}\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(content)
    
    return log_file


def generate_weekly_digest(topic: str, callback: Optional[Callable] = None) -> str:
    """Generate a weekly digest for a topic."""
    handler = ConversationHandler()
    
    # Construct query for weekly summary (English)
    query = f"What are the most interesting things that happened this week in {topic}?"
    
    # Process the query
    response = handler.process_message(query)
    
    # Log the digest
    log_file = log_digest(response, topic)
    
    # Call callback if provided
    if callback:
        callback(topic, response, log_file)
    
    return response


def run_scheduled_digests():
    """Run scheduled digests for all configured topics."""
    prefs = load_preferences()
    
    if not prefs.weekly_digest_enabled:
        return
    
    console.print(f"\n🤖 Running scheduled weekly digest...\n", style="bold blue")
    
    for topic in prefs.weekly_digest_topics:
        try:
            console.print(f"📊 Generating digest for: {topic}")
            digest = generate_weekly_digest(topic)
            console.print(f"✅ Digest for {topic} complete\n")
        except Exception as e:
            console.print(f"❌ Error generating digest for {topic}: {e}", style="red")


def schedule_weekly_digest(day: str = "sunday", time_str: str = "09:00"):
    """Schedule the weekly digest job."""
    import os
    test_interval = os.getenv("DIGEST_TEST_INTERVAL_MINUTES")
    if test_interval:
        minutes = int(test_interval)
        schedule.every(minutes).minutes.do(run_scheduled_digests)
        console.print(f"🧪 TEST MODE: digest scheduled every {minutes} minute(s)")
        return
    day_map = {
        "sunday": schedule.every().sunday,
        "monday": schedule.every().monday,
        "tuesday": schedule.every().tuesday,
        "wednesday": schedule.every().wednesday,
        "thursday": schedule.every().thursday,
        "friday": schedule.every().friday,
        "saturday": schedule.every().saturday,
    }
    
    if day.lower() in day_map:
        day_map[day.lower()].at(time_str).do(run_scheduled_digests)
        console.print(f"📅 Weekly digest scheduled for {day} at {time_str}")
    else:
        console.print(f"❌ Invalid day: {day}", style="red")


def run_scheduler_loop():
    """Run the scheduler loop (blocking)."""
    console.print("🕐 Scheduler started. Press Ctrl+C to stop.", style="dim")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def start_scheduler_thread(day: str = "sunday", time_str: str = "09:00"):
    """Start the scheduler in a background thread."""
    prefs = load_preferences()
    
    if prefs.weekly_digest_enabled:
        schedule_weekly_digest(day, time_str)
        
        thread = threading.Thread(target=run_scheduler_loop, daemon=True)
        thread.start()
        
        return thread
    
    return None


def get_next_run_time() -> Optional[datetime]:
    """Get the next scheduled run time."""
    jobs = schedule.get_jobs()
    if jobs:
        return jobs[0].next_run
    return None


def get_scheduler_status(language: str = "he") -> str:
    """Get the current scheduler status."""
    prefs = load_preferences()
    next_run = get_next_run_time()
    
    if language == "he":
        if not prefs.weekly_digest_enabled:
            return "⏸️ דייג'סט שבועי **כבוי**"
        
        status = f"""
📅 **סטטוס דייג'סט שבועי**

• מצב: מופעל ✅
• יום: {prefs.weekly_digest_day}
• נושאים: {', '.join(prefs.weekly_digest_topics)}
"""
        if next_run:
            status += f"• ריצה הבאה: {next_run.strftime('%Y-%m-%d %H:%M')}"
        
        return status
    else:
        if not prefs.weekly_digest_enabled:
            return "⏸️ Weekly digest is **disabled**"
        
        status = f"""
📅 **Weekly Digest Status**

• Status: Enabled ✅
• Day: {prefs.weekly_digest_day}
• Topics: {', '.join(prefs.weekly_digest_topics)}
"""
        if next_run:
            status += f"• Next run: {next_run.strftime('%Y-%m-%d %H:%M')}"
        
        return status


def run_digest_now(topics: Optional[list[str]] = None):
    """Run digest immediately for specified topics."""
    prefs = load_preferences()
    topics = topics or prefs.weekly_digest_topics
    
    results = {}
    for topic in topics:
        try:
            digest = generate_weekly_digest(topic)
            results[topic] = digest
        except Exception as e:
            results[topic] = f"Error: {e}"
    
    return results
