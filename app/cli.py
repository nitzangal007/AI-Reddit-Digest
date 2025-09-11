# app/cli.py
# CLI entry point: parse arguments, fetch posts, summarize them

import argparse
from app.config import DEFAULT_SUBREDDIT, TOP_LIMIT
from app import reddit_client as rc
from app.summarize import summarize_text


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


def main() -> None:
    """
    Main function to parse arguments, fetch posts, and summarize them.
    """
    parser = build_parser()
    args = parser.parse_args()

    subreddit = args.subreddit
    limit = args.limit

    print(f"Fetching top {limit} posts from r/{subreddit}...\n")

    # Fetch posts using the reddit_client module
    posts = rc.get_posts_with_comments(
        subreddit=subreddit,
        sort="top",
        time_filter="day",
        requested=limit,
        comment_limit=5,  # Fetch top 5 comments per post
        min_score=None    # No minimum score filter for now
    )

    if not posts:
        print("No posts found.")
        return

    for i, post in enumerate(posts, start=1):
        title = post.get("title", "No Title")
        selftext = post.get("selftext", "")
        combined_text = f"{title}\n\n{selftext}"

        print(f"Post {i}: {title}")
        print(f"URL: {post.get('permalink', 'N/A')}")
        print(f"Score: {post.get('score', 0)}")

        # Summarize the post content
        summary = summarize_text(combined_text)
        print(f"Summary:\n{summary}\n")

        # Print top comments
        comments = post.get("comments", [])
        if comments:
            print("Top Comments:")
            for c in comments[:5]:  # Show top 5 comments
                author = c.get("author", "[deleted]")
                body = c.get("body", "")
                score = c.get("score", 0)
                print(f"- {body} (by {author}, ↑{score})")
            print("\n" + "-"*40 + "\n")
        else:
            print("No comments available.\n" + "-"*40 + "\n")
if __name__ == "__main__":
    main()
