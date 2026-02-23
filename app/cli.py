# app/cli.py
# CLI entry point: parse arguments, run chat mode, or fetch posts

import argparse
import sys
from app.config import DEFAULT_SUBREDDIT, TOP_LIMIT
from app import reddit_client as rc
from app.summarize import summarize_post


def build_parser() -> argparse.ArgumentParser:
    """
    Build the argument parser and define available CLI flags.
    """
    parser = argparse.ArgumentParser(
        prog="reddit-digest",
        description="🤖 Reddit Digest - AI-powered Reddit summarizer with chat interface"
    )

    # Mode selection
    parser.add_argument(
        "--chat", "-c",
        action="store_true",
        help="Start interactive chat mode (recommended)"
    )
    
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Ask a single question and get a response"
    )
    
    # Scheduler
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run the weekly digest scheduler"
    )
    
    parser.add_argument(
        "--digest-now",
        action="store_true",
        help="Run weekly digest immediately for configured topics"
    )

    # Legacy mode arguments
    parser.add_argument(
        "--subreddit", "-s",
        default=DEFAULT_SUBREDDIT,
        help=f"[Legacy] Subreddit name (default: {DEFAULT_SUBREDDIT})"
    )

    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=TOP_LIMIT,
        help=f"[Legacy] Number of posts to fetch (default: {TOP_LIMIT})"
    )
    
    parser.add_argument(
        "--sort",
        choices=["top", "hot", "new"],
        default="top",
        help="[Legacy] Sort method (default: top)"
    )
    
    parser.add_argument(
        "--time", "-t",
        choices=["hour", "day", "week", "month", "year", "all"],
        default="day",
        help="[Legacy] Time filter for top posts (default: day)"
    )
    
    parser.add_argument(
        "--language", "-l",
        choices=["he", "en"],
        default="he",
        help="Language for responses (default: he)"
    )

    return parser


def run_legacy_mode(args):
    """Run the legacy CLI mode (fetch and print posts)."""
    subreddit = args.subreddit
    limit = args.limit

    print(f"Fetching top {limit} posts from r/{subreddit}...\n")

    # Fetch posts using the reddit_client module
    posts = rc.get_posts_with_comments(
        subreddit=subreddit,
        sort=args.sort,
        time_filter=args.time,
        requested=limit,
        comment_limit=5,
        min_score=None
    )

    if not posts:
        print("No posts found.")
        return

    for i, post in enumerate(posts, start=1):
        title = post.get("title", "No Title")
        selftext = post.get("selftext", "")

        print(f"Post {i}: {title}")
        print(f"URL: {post.get('permalink', 'N/A')}")
        print(f"Score: {post.get('score', 0)}")

        # Summarize the post content
        summary = summarize_post(title, selftext, max_char=320)
        print(f"Summary:\n{summary}\n")

        # Print top comments
        comments = post.get("comments", [])
        if comments:
            print("Top Comments:")
            for c in comments[:5]:
                author = c.get("author", "[deleted]")
                body = c.get("body", "")
                score = c.get("score", 0)
                print(f"- {body} (by {author}, ↑{score})")
            print("\n" + "-"*40 + "\n")
        else:
            print("No comments available.\n" + "-"*40 + "\n")


def run_chat_mode():
    """Run the interactive chat mode."""
    from app.conversation import run_interactive_chat
    run_interactive_chat()


def run_single_query(query: str, language: str = "he"):
    """Run a single query and print the response."""
    from app.conversation import ConversationHandler
    from app.formatter import print_response, print_thinking
    
    handler = ConversationHandler()
    handler.context.language = language
    
    print_thinking(language)
    response = handler.process_message(query)
    print_response(response)


def run_scheduler():
    """Run the weekly digest scheduler."""
    from app.scheduler import start_scheduler_thread, run_scheduler_loop, get_scheduler_status
    from app.user_preferences import load_preferences
    from app.formatter import console
    
    prefs = load_preferences()
    
    if not prefs.weekly_digest_enabled:
        console.print("⚠️  Weekly digest is disabled. Enable it first with --chat mode.", style="bold yellow")
        console.print("    Use: /weekly on", style="dim")
        return
    
    console.print(get_scheduler_status(prefs.language))
    console.print("\n🕐 Starting scheduler... Press Ctrl+C to stop.\n", style="dim")
    
    try:
        start_scheduler_thread(prefs.weekly_digest_day, "09:00")
        run_scheduler_loop()
    except KeyboardInterrupt:
        console.print("\n👋 Scheduler stopped.", style="bold")


def run_digest_immediately():
    """Run digest for all configured topics right now."""
    from app.scheduler import run_digest_now
    from app.user_preferences import load_preferences
    from app.formatter import console, print_response, print_divider
    
    prefs = load_preferences()
    topics = prefs.weekly_digest_topics or ["tech", "ai"]
    
    console.print(f"🚀 Running digest for topics: {', '.join(topics)}\n", style="bold blue")
    
    results = run_digest_now(topics)
    
    for topic, digest in results.items():
        console.print(f"\n📊 **{topic.upper()}**", style="bold cyan")
        print_response(digest, title=f"📰 {topic}")
        print_divider()


def main() -> None:
    """
    Main function to parse arguments and run the appropriate mode.
    """
    parser = build_parser()
    args = parser.parse_args()

    # Priority order: chat > query > schedule > digest-now > legacy
    if args.chat:
        run_chat_mode()
    elif args.query:
        run_single_query(args.query, args.language)
    elif args.schedule:
        run_scheduler()
    elif args.digest_now:
        run_digest_immediately()
    else:
        # If no specific mode, show help and suggest chat mode
        if len(sys.argv) == 1:
            print("🤖 Reddit Digest - AI-powered Reddit summarizer\n")
            print("Quick start:")
            print("  python -m app --chat     # Start interactive chat")
            print("  python -m app -q 'מה חדש בAI?'  # Ask a single question")
            print()
            parser.print_help()
        else:
            # Legacy mode for backward compatibility
            run_legacy_mode(args)


if __name__ == "__main__":
    main()
