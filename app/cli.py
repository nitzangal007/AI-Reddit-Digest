# app/cli.py
# CLI entry point: parse arguments, fetch posts, summarize them

import argparse
from .config import DEFAULT_SUBREDDIT, TOP_LIMIT
from .reddit_client import top_posts
from .reddit_client import hot_post_and_comments
from .summarize import summarize_text


def build_parser() -> argparse.ArgumentParser:
    """
    Build the argument parser and define available CLI flags.
    """
    parser = argparse.ArgumentParser(
        prog="app",
        description="Fetch and summarize Reddit posts"
    )

    # Subreddit name (string). Default comes from config.
    parser.add_argument(
        "--subreddit", "-s",
        default=DEFAULT_SUBREDDIT,
        help=f"name of subreddit (default: {DEFAULT_SUBREDDIT})"
    )

    # Number of posts to fetch (integer). Default comes from config.
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=TOP_LIMIT,
        help=f"how many posts to fetch (default: {TOP_LIMIT})"
    )

    # Example of future flags (not active yet):
    # parser.add_argument("--sort", choices=["top", "hot", "new", "rising"], default="top")
    # parser.add_argument("--time", choices=["day", "week", "month", "year", "all"], default="day")

    return parser


def main(argv=None) -> None:
    """
    CLI entry point.
    `argv` allows injecting arguments for testing. If None, uses sys.argv.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    subreddit = args.subreddit
    limit = args.limit

    for i, post in enumerate(hot_post_and_comments(subreddit, limit, comment_limit=3), start=1):
        print(f"{i}. {post['title']} (score: {post['score']})")
        print(f"URL: {post['url']}")
        print("Comments:")
        for comment in post.get("comments", []):
            print(f" - {comment}")
        print()

if __name__ == "__main__":
    main()
