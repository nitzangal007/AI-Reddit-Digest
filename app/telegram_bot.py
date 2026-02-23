# app/telegram_bot.py
# Telegram bot entry point with handlers and onboarding flow

import os
import asyncio
import logging
from datetime import time
from typing import Optional

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ConversationHandler as TGConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from .config import TOPIC_SUBREDDIT_MAP
from .user_store import (
    get_or_create_user, 
    get_user, 
    update_user, 
    delete_user,
    get_user_preferences_summary,
    get_users_for_daily_digest,
    get_users_for_weekly_digest,
    TelegramUserPreferences
)
from .conversation import ConversationHandler as RedditConversationHandler
from .scheduler import generate_weekly_digest

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load token from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN environment variable. Add it to your .env file.")


# =============================================================================
# Onboarding States
# =============================================================================
(
    ONBOARDING_SUBREDDITS,
    ONBOARDING_TOPICS,
    ONBOARDING_INTEREST,
    ONBOARDING_FREQUENCY,
    ONBOARDING_EMAIL,
) = range(5)

# Suggested subreddits by category
SUGGESTED_SUBREDDITS = {
    "🤖 AI & Tech": ["MachineLearning", "artificial", "technology", "programming"],
    "🎮 Gaming": ["gaming", "Games", "pcgaming", "PS5"],
    "⚽ Sports": ["sports", "nba", "soccer", "nfl"],
    "💰 Finance & Crypto": ["CryptoCurrency", "Bitcoin", "stocks", "investing"],
    "🔬 Science": ["science", "space", "Physics", "biology"],
    "📰 News & Politics": ["worldnews", "news", "politics"],
}

INTEREST_TYPES = {
    "🔥 Top Posts": "top",
    "💥 Controversial": "controversial",
    "📚 Tutorials & Learning": "tutorials",
    "🚀 Product Launches": "product_launches",
}

FREQUENCY_OPTIONS = {
    "📅 Daily": "daily",
    "📆 Weekly": "weekly",
    "📅📆 Both": "both",
    "⏭️ Skip (I'll ask manually)": "none",
}


# =============================================================================
# Per-User Conversation Handler Cache
# =============================================================================
_user_handlers: dict[int, RedditConversationHandler] = {}


def get_reddit_handler(chat_id: int) -> RedditConversationHandler:
    """Get or create a Reddit conversation handler for a user."""
    if chat_id not in _user_handlers:
        _user_handlers[chat_id] = RedditConversationHandler()
    return _user_handlers[chat_id]


# =============================================================================
# Command Handlers
# =============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command - begin onboarding or show settings."""
    chat_id = update.effective_chat.id
    username = update.effective_user.username or ""
    
    user = get_or_create_user(chat_id, username)
    
    if user.onboarding_complete:
        # User already onboarded - show settings
        await update.message.reply_text(
            f"👋 Welcome back!\n\n{get_user_preferences_summary(user)}\n"
            "Use /help to see available commands."
        )
        return TGConversationHandler.END
    
    # Start onboarding
    await update.message.reply_text(
        "👋 **Welcome to Reddit Digest Bot!**\n\n"
        "I'll help you stay updated with the best content from Reddit.\n"
        "Let's set up your preferences in a few quick steps.\n\n"
        "**Step 1/5: Which subreddits interest you?**\n\n"
        "You can:\n"
        "• Choose from categories below\n"
        "• Type subreddit names (comma-separated)\n"
        "• Or type 'skip' to use defaults",
        parse_mode='Markdown'
    )
    
    # Show category buttons
    keyboard = [[cat] for cat in SUGGESTED_SUBREDDITS.keys()]
    keyboard.append(["⏭️ Skip (use defaults)"])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text("Choose a category or type subreddit names:", reply_markup=reply_markup)
    
    user.onboarding_step = "ask_subreddits"
    update_user(user)
    
    return ONBOARDING_SUBREDDITS


async def onboarding_subreddits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle subreddit selection during onboarding."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    text = update.message.text
    
    if text in SUGGESTED_SUBREDDITS:
        # User selected a category
        user.subreddits = SUGGESTED_SUBREDDITS[text]
        await update.message.reply_text(
            f"✅ Great! I'll follow: {', '.join(user.subreddits)}"
        )
    elif "skip" in text.lower():
        # Use defaults
        user.subreddits = ["MachineLearning", "technology", "programming"]
        await update.message.reply_text(
            f"✅ Using defaults: {', '.join(user.subreddits)}"
        )
    else:
        # User typed custom subreddits
        subs = [s.strip().replace("r/", "") for s in text.split(",")]
        user.subreddits = [s for s in subs if s]
        if not user.subreddits:
            user.subreddits = ["MachineLearning", "technology"]
        await update.message.reply_text(
            f"✅ Following: {', '.join(user.subreddits)}"
        )
    
    update_user(user)
    
    # Move to topics
    await update.message.reply_text(
        "**Step 2/5: What topics interest you most?**\n\n"
        "Choose one or type your own:",
        parse_mode='Markdown'
    )
    
    keyboard = [[topic] for topic in TOPIC_SUBREDDIT_MAP.keys()][:8]
    keyboard.append(["⏭️ Skip (use defaults)"])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Select topics:", reply_markup=reply_markup)
    
    user.onboarding_step = "ask_topics"
    update_user(user)
    
    return ONBOARDING_TOPICS


async def onboarding_topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle topic selection during onboarding."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    text = update.message.text.lower()
    
    if "skip" in text:
        user.topics = ["tech", "ai"]
    elif text in TOPIC_SUBREDDIT_MAP:
        user.topics = [text]
    else:
        # Parse custom topics
        topics = [t.strip().lower() for t in text.split(",")]
        user.topics = [t for t in topics if t in TOPIC_SUBREDDIT_MAP] or ["tech", "ai"]
    
    await update.message.reply_text(f"✅ Topics set: {', '.join(user.topics)}")
    update_user(user)
    
    # Move to interest type
    keyboard = [[interest] for interest in INTEREST_TYPES.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "**Step 3/5: What kind of posts interest you most?**",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    user.onboarding_step = "ask_interest"
    update_user(user)
    
    return ONBOARDING_INTEREST


async def onboarding_interest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle interest type selection during onboarding."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    text = update.message.text
    
    if text in INTEREST_TYPES:
        user.interest_type = INTEREST_TYPES[text]
    else:
        user.interest_type = "top"
    
    await update.message.reply_text(f"✅ Interest type: {user.interest_type}")
    update_user(user)
    
    # Move to frequency
    keyboard = [[freq] for freq in FREQUENCY_OPTIONS.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "**Step 4/5: How often would you like digests?**\n\n"
        "I can send you automatic summaries daily, weekly, or both!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    user.onboarding_step = "ask_frequency"
    update_user(user)
    
    return ONBOARDING_FREQUENCY


async def onboarding_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle frequency selection during onboarding."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    text = update.message.text
    
    if text in FREQUENCY_OPTIONS:
        freq = FREQUENCY_OPTIONS[text]
        if freq == "daily":
            user.daily_digest_enabled = True
            user.weekly_digest_enabled = False
        elif freq == "weekly":
            user.daily_digest_enabled = False
            user.weekly_digest_enabled = True
        elif freq == "both":
            user.daily_digest_enabled = True
            user.weekly_digest_enabled = True
        else:
            user.daily_digest_enabled = False
            user.weekly_digest_enabled = False
    
    status = []
    if user.daily_digest_enabled:
        status.append("daily")
    if user.weekly_digest_enabled:
        status.append("weekly")
    status_text = " & ".join(status) if status else "manual only"
    
    await update.message.reply_text(f"✅ Digest frequency: {status_text}")
    update_user(user)
    
    # Move to email (optional)
    keyboard = [["⏭️ Skip (no email)"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "**Step 5/5: Email notifications (optional)**\n\n"
        "Want digests sent to your email too?\n"
        "Type your email or skip:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    user.onboarding_step = "ask_email"
    update_user(user)
    
    return ONBOARDING_EMAIL


async def onboarding_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle email input during onboarding."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    text = update.message.text
    
    if "skip" not in text.lower() and "@" in text:
        user.email = text.strip()
        await update.message.reply_text(f"✅ Email set: {user.email}")
    else:
        user.email = ""
        await update.message.reply_text("✅ No email configured")
    
    # Complete onboarding
    user.onboarding_complete = True
    user.onboarding_step = ""
    update_user(user)
    
    await update.message.reply_text(
        "🎉 **Setup complete!**\n\n"
        f"{get_user_preferences_summary(user)}\n"
        "You can now:\n"
        "• Ask me anything about Reddit (just type!)\n"
        "• Use /settings to view/change preferences\n"
        "• Use /help for all commands",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    
    return TGConversationHandler.END


async def cancel_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the onboarding process."""
    await update.message.reply_text(
        "Onboarding cancelled. Use /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return TGConversationHandler.END


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command - show current preferences."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    
    if not user:
        await update.message.reply_text("Please use /start first to set up your preferences.")
        return
    
    await update.message.reply_text(get_user_preferences_summary(user), parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """📚 **Available Commands**

**Setup & Settings:**
• /start - Begin setup or view settings
• /settings - Show your preferences
• /reset - Clear all preferences and restart

**Customize:**
• /set_subreddits - Change followed subreddits
• /set_topics - Change topics of interest
• /set_frequency - Change digest frequency

**Digests:**
• /weekly on - Enable weekly digest
• /weekly off - Disable weekly digest
• /digest - Get a digest right now

**Other:**
• /help - Show this message
• /topics - List available topics

**Chat:**
Just type naturally! Ask things like:
• "What's new in AI this week?"
• "Show me trending posts in gaming"
• "Summarize the top tech news"
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /topics command - list available topics."""
    topics_list = "\n".join([f"• **{topic}**" for topic in TOPIC_SUBREDDIT_MAP.keys()])
    await update.message.reply_text(
        f"📋 **Available Topics:**\n\n{topics_list}\n\n"
        "Use /set_topics to change your preferences.",
        parse_mode='Markdown'
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset command - clear preferences."""
    chat_id = update.effective_chat.id
    delete_user(chat_id)
    
    # Clear cached handler
    if chat_id in _user_handlers:
        del _user_handlers[chat_id]
    
    await update.message.reply_text(
        "🔄 Your preferences have been reset.\n"
        "Use /start to set up again."
    )


async def weekly_toggle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /weekly on|off command."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    
    if not user:
        await update.message.reply_text("Please use /start first.")
        return
    
    text = update.message.text.lower()
    if "on" in text:
        user.weekly_digest_enabled = True
        update_user(user)
        await update.message.reply_text("✅ Weekly digest enabled!")
    elif "off" in text:
        user.weekly_digest_enabled = False
        update_user(user)
        await update.message.reply_text("❌ Weekly digest disabled.")
    else:
        status = "enabled" if user.weekly_digest_enabled else "disabled"
        await update.message.reply_text(
            f"Weekly digest is currently **{status}**.\n"
            "Use `/weekly on` or `/weekly off` to change.",
            parse_mode='Markdown'
        )


async def set_subreddits_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /set_subreddits command."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    
    if not user:
        await update.message.reply_text("Please use /start first.")
        return
    
    # Check if arguments provided
    if context.args:
        subs = [s.strip().replace("r/", "") for s in " ".join(context.args).split(",")]
        user.subreddits = [s for s in subs if s]
        update_user(user)
        await update.message.reply_text(f"✅ Subreddits updated: {', '.join(user.subreddits)}")
    else:
        current = ', '.join(user.subreddits) if user.subreddits else 'None'
        await update.message.reply_text(
            f"**Current subreddits:** {current}\n\n"
            "To change, use:\n"
            "`/set_subreddits MachineLearning, Python, technology`",
            parse_mode='Markdown'
        )


async def set_topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /set_topics command."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    
    if not user:
        await update.message.reply_text("Please use /start first.")
        return
    
    if context.args:
        topics = [t.strip().lower() for t in " ".join(context.args).split(",")]
        valid_topics = [t for t in topics if t in TOPIC_SUBREDDIT_MAP]
        if valid_topics:
            user.topics = valid_topics
            update_user(user)
            await update.message.reply_text(f"✅ Topics updated: {', '.join(user.topics)}")
        else:
            await update.message.reply_text("❌ No valid topics found. Use /topics to see available options.")
    else:
        current = ', '.join(user.topics) if user.topics else 'None'
        await update.message.reply_text(
            f"**Current topics:** {current}\n\n"
            "To change, use:\n"
            "`/set_topics ai, programming, gaming`\n\n"
            "Use /topics to see available options.",
            parse_mode='Markdown'
        )


async def set_frequency_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /set_frequency command."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    
    if not user:
        await update.message.reply_text("Please use /start first.")
        return
    
    if context.args:
        freq = context.args[0].lower()
        if freq == "daily":
            user.daily_digest_enabled = True
            user.weekly_digest_enabled = False
        elif freq == "weekly":
            user.daily_digest_enabled = False
            user.weekly_digest_enabled = True
        elif freq == "both":
            user.daily_digest_enabled = True
            user.weekly_digest_enabled = True
        elif freq == "none" or freq == "off":
            user.daily_digest_enabled = False
            user.weekly_digest_enabled = False
        else:
            await update.message.reply_text("❌ Invalid option. Use: daily, weekly, both, or none")
            return
        
        update_user(user)
        await update.message.reply_text(f"✅ Frequency updated!")
    else:
        status = []
        if user.daily_digest_enabled:
            status.append("Daily")
        if user.weekly_digest_enabled:
            status.append("Weekly")
        current = " & ".join(status) if status else "None (manual only)"
        
        await update.message.reply_text(
            f"**Current frequency:** {current}\n\n"
            "To change, use:\n"
            "`/set_frequency daily|weekly|both|none`",
            parse_mode='Markdown'
        )


async def digest_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /digest command - get a digest immediately."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    
    if not user:
        await update.message.reply_text("Please use /start first.")
        return
    
    await update.message.reply_text("⏳ Generating your digest... This may take a moment.")
    
    try:
        # Generate digest using user's topics
        topics = user.topics or ["tech", "ai"]
        handler = get_reddit_handler(chat_id)
        
        for topic in topics[:2]:  # Limit to 2 topics for quick response
            query = f"What are the most interesting things happening in {topic}?"
            # Run in thread to avoid blocking
            response = await asyncio.to_thread(handler.process_message, query)
            
            await update.message.reply_text(
                f"📊 **{topic.upper()} Digest:**\n\n{response}",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error generating digest: {e}")
        await update.message.reply_text(f"❌ Error generating digest: {str(e)}")


# =============================================================================
# Message Handler (Natural Chat)
# =============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages - pass to conversation engine."""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    
    if not user or not user.onboarding_complete:
        await update.message.reply_text(
            "Please complete setup first with /start"
        )
        return
    
    user_message = update.message.text
    
    # Get the Reddit conversation handler for this user
    handler = get_reddit_handler(chat_id)
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        # Run synchronous Reddit/AI calls in a thread pool to avoid blocking
        response = await asyncio.to_thread(handler.process_message, user_message)
        
        # Handle quit command
        if response == "__QUIT__":
            await update.message.reply_text("Goodbye! Use /start to chat again.")
            return
        
        # Send response (split if too long)
        if len(response) > 4000:
            # Split long messages
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i+4000])
        else:
            await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(f"Sorry, I encountered an error: {str(e)}")


# =============================================================================
# Scheduled Digest Jobs
# =============================================================================

async def send_daily_digests(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job to send daily digests to subscribed users."""
    from datetime import datetime
    
    current_hour = datetime.now().hour
    users = get_users_for_daily_digest(current_hour)
    
    logger.info(f"Running daily digest job for hour {current_hour}, found {len(users)} users")
    
    for user in users:
        try:
            handler = get_reddit_handler(user.chat_id)
            
            for topic in user.topics[:2]:
                query = f"What are the most interesting things today in {topic}?"
                response = handler.process_message(query)
                
                await context.bot.send_message(
                    chat_id=user.chat_id,
                    text=f"📅 **Daily {topic.upper()} Digest:**\n\n{response}",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error sending daily digest to {user.chat_id}: {e}")


async def send_weekly_digests(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job to send weekly digests to subscribed users."""
    from datetime import datetime
    
    current_day = datetime.now().strftime("%A").lower()
    current_hour = datetime.now().hour
    users = get_users_for_weekly_digest(current_day, current_hour)
    
    logger.info(f"Running weekly digest job for {current_day} hour {current_hour}, found {len(users)} users")
    
    for user in users:
        try:
            handler = get_reddit_handler(user.chat_id)
            
            for topic in user.topics[:2]:
                query = f"What are the most interesting things this week in {topic}?"
                response = handler.process_message(query)
                
                await context.bot.send_message(
                    chat_id=user.chat_id,
                    text=f"📆 **Weekly {topic.upper()} Digest:**\n\n{response}",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error sending weekly digest to {user.chat_id}: {e}")


# =============================================================================
# Main Application Setup
# =============================================================================

def create_application() -> Application:
    """Create and configure the Telegram bot application."""
    
    # Build application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Onboarding conversation handler
    onboarding_handler = TGConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ONBOARDING_SUBREDDITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_subreddits)],
            ONBOARDING_TOPICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_topics)],
            ONBOARDING_INTEREST: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_interest)],
            ONBOARDING_FREQUENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_frequency)],
            ONBOARDING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel_onboarding)],
        allow_reentry=True,
    )
    
    # Add handlers
    application.add_handler(onboarding_handler)
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("topics", topics_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("weekly", weekly_toggle_command))
    application.add_handler(CommandHandler("set_subreddits", set_subreddits_command))
    application.add_handler(CommandHandler("set_topics", set_topics_command))
    application.add_handler(CommandHandler("set_frequency", set_frequency_command))
    application.add_handler(CommandHandler("digest", digest_now_command))
    
    # Message handler for natural chat (must be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Schedule jobs for digests
    job_queue = application.job_queue
    
    # Run digest checks every hour
    job_queue.run_repeating(send_daily_digests, interval=3600, first=60)  # Every hour
    job_queue.run_repeating(send_weekly_digests, interval=3600, first=120)  # Every hour, offset
    
    return application


def main():
    """Start the Telegram bot."""
    print("🤖 Starting Reddit Digest Telegram Bot...")
    print("Press Ctrl+C to stop.\n")
    
    application = create_application()
    
    # Run with long polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
