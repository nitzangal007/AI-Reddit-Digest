# manual_preview.py — ad-hoc manual tests runner (print-only)
# Goal: run "black-box" style tests against reddit_client using real API calls,
# and print results in the same format the user expects from "print_top_day".
#
# ▶ How to run:
#    python manual_preview.py
#    (or) python -m app.manual_preview             # if this file lives under package "app"
#
# IMPORTANT: This module does not use pytest/unittest. It prints human-readable
# check outputs so you can eyeball the results quickly and compare across runs.

from __future__ import annotations

# Robust imports: support both "app.*" package layout and flat layout.
try:
    from app import reddit_client as rc
    from app.config import DEFAULT_SUBREDDIT
except Exception:  # pragma: no cover
    import reddit_client as rc  # type: ignore
    from config import DEFAULT_SUBREDDIT  # type: ignore

from typing import List, Dict, Any, Iterable
import time

# ------------- Formatting helpers (keep output stable & comparable) -------------

def _trim(text: str, max_len: int = 140) -> str:
    """
    Make a single-line, length-bounded snippet:
    - Replace newlines with spaces
    - Strip trailing/leading whitespace
    - Ellipsize with '…' when longer than max_len
    """
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= max_len else text[: max_len - 1] + "…"

def _fmt_score(n: int) -> str:
    """Format numbers with thousands separators (e.g., 1,234)."""
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)

def _format_comment_line(c: Dict[str, Any], max_len: int = 140) -> str:
    """
    Render a single comment line with indentation and optional reply context.
    Expected keys (rc.CommentData shape):
      - body, score, author
      - depth (optional), parent_author (optional), parent_id (optional)
    """
    depth = int(c.get("depth", 0) or 0)
    indent = "  " * depth
    author = c.get("author", "[deleted]")
    body = _trim(c.get("body", ""), max_len=max_len)
    score = _fmt_score(c.get("score", 0))
    parent_author = c.get("parent_author")
    if depth > 0 and parent_author:
        return f"{indent}↳ {body} — {author} (↑{score})  (reply to {parent_author})"
    return f"{indent}{body} — {author} (↑{score})"

def _print_posts_block(
    posts: Iterable[Dict[str, Any]],
    *, subreddit: str, sort: str, time_filter: str | None, comments_to_show: int
) -> None:
    """
    Print a list of posts in a stable, comparable format similar to print_top_day.
    - Shows: title, score, trimmed selftext, author, time window label, permalink
    - Then prints up to N comments using _format_comment_line.
    """
    window_label = f"{time_filter}" if (sort == "top" and time_filter) else sort
    print(f"\n===== Subreddit: r/{subreddit} — Sort: {sort} — Window: {window_label} =====\n")

    for i, p in enumerate(posts, start=1):
        score = _fmt_score(p.get("score", 0))
        title = p.get("title", "").strip()
        selftext = _trim(p.get("selftext", ""), max_len=300)
        author = p.get("author", "[deleted]")
        permalink = p.get("permalink", p.get("url", ""))
        comments = list(p.get("comments", []))
        shown = min(comments_to_show, len(comments))

        print(f"{i}) [{title}]  (score: {score})")
        print(f"   Selftext: {selftext}")
        print(f"   Subreddit: r/{subreddit} | Author: {author} | Time: {window_label} | ")
        print(f"   URL: {permalink}\n")
        print(f"   Top comments ({shown}):")
        for c in comments[:comments_to_show]:
            print("   " + _format_comment_line(c, max_len=140))
        print()  # blank line between posts

# ------------- Fetch helper (single source of truth for all tests) -------------

def _fetch_with_comments(
    *, subreddit: str, sort: rc.Sort, requested: int, comments: int,
    time_filter: rc.TopWindow = "day", min_score: int | None = None
) -> List[Dict[str, Any]]:
    """
    Call reddit_client.get_posts_with_comments with consistent arguments.
    This keeps test functions tiny and ensures identical behavior everywhere.
    """
    return rc.get_posts_with_comments(
        subreddit,
        sort=sort,
        requested=requested,
        comment_limit=comments,
        min_score=min_score,
        time_filter=time_filter,
    )

# ============================ TEST FUNCTIONS ============================
# Each test prints a short banner, fetches posts+comments, prints the block,
# and (when possible) prints a PASS/FAIL style line for a sanity check.
# The goal is "manual preview", so we prefer readable prints over hard asserts.

def test_top_day_texty_subreddit(
    subreddit: str = "AskReddit", posts: int = 5, comments: int = 3, min_score: int | None = None
) -> None:
    """
    Purpose:
      Validate that for a text-heavy subreddit (r/AskReddit) we usually get the
      requested number of posts when using the default "text-only posts" filter.
    What we check:
      - Returned length is <= requested and ideally == requested (not a hard assert).
      - Printing format matches our standard block.
    """
    data = _fetch_with_comments(
        subreddit=subreddit, sort="top", requested=posts, comments=comments, time_filter="day", min_score=min_score
    )
    _print_posts_block(data, subreddit=subreddit, sort="top", time_filter="day", comments_to_show=comments)
    print(f"[INFO] Received {len(data)}/{posts} posts from r/{subreddit} (expected ~{posts}).\n")

def test_top_day_vs_week_on_chatgpt(
    posts: int = 5, comments: int = 3, min_score: int | None = None
) -> None:
    """
    Purpose:
      Demonstrate impact of the time window on r/ChatGPT where many posts are links/images.
    What we check:
      - top/day may return fewer than requested due to our "text-only" post filter.
      - top/week should typically return more candidates and may better meet 'requested'.
    """
    sub = "ChatGPT"
    day_data = _fetch_with_comments(subreddit=sub, sort="top", requested=posts, comments=comments, time_filter="day", min_score=min_score)
    week_data = _fetch_with_comments(subreddit=sub, sort="top", requested=posts, comments=comments, time_filter="week", min_score=min_score)
    _print_posts_block(day_data,  subreddit=sub, sort="top", time_filter="day",  comments_to_show=comments)
    _print_posts_block(week_data, subreddit=sub, sort="top", time_filter="week", comments_to_show=comments)
    print(f"[INFO] r/{sub} day={len(day_data)}/{posts} vs week={len(week_data)}/{posts}.\n")

def test_hot_basic(
    subreddit: str = "MachineLearning", posts: int = 5, comments: int = 3, min_score: int | None = None
) -> None:
    """
    Purpose:
      Verify 'hot' sorting returns up to the requested count and prints correctly.
    What we check:
      - Output formatting parity with TOP tests.
      - Returned length is reasonable (<= requested; ideally close to requested).
    """
    data = _fetch_with_comments(subreddit=subreddit, sort="hot", requested=posts, comments=comments, time_filter="day", min_score=min_score)
    _print_posts_block(data, subreddit=subreddit, sort="hot", time_filter=None, comments_to_show=comments)
    print(f"[INFO] HOT: received {len(data)}/{posts} from r/{subreddit}.\n")

def test_new_basic(
    subreddit: str = "ChatGPT", posts: int = 5, comments: int = 3, min_score: int | None = None
) -> None:
    """
    Purpose:
      Verify 'new' sorting works and adheres to the text-only post filter.
    What we check:
      - Often returns fewer than requested for subs heavy on link/image posts.
    """
    data = _fetch_with_comments(subreddit=subreddit, sort="new", requested=posts, comments=comments, time_filter="day", min_score=min_score)
    _print_posts_block(data, subreddit=subreddit, sort="new", time_filter=None, comments_to_show=comments)
    print(f"[INFO] NEW: received {len(data)}/{posts} from r/{subreddit}.\n")

def test_comment_limit_variations(
    subreddit: str = "AskReddit", posts: int = 2, comment_limits: Iterable[int] = (0, 1, 5)
) -> None:
    """
    Purpose:
      Ensure comment_limit is honored. We fetch the same 'posts' count multiple times
      with different 'comment_limits' to compare output sizes of the comments sections.
    What we check:
      - Each printed block shows 'Top comments (shown)' equal to the requested limit or fewer if not available.
    """
    for limit in comment_limits:
        data = _fetch_with_comments(subreddit=subreddit, sort="top", requested=posts, comments=limit, time_filter="day")
        _print_posts_block(data, subreddit=subreddit, sort="top", time_filter="day", comments_to_show=limit)
        print(f"[INFO] comment_limit={limit} — verified visually above.\n")

def test_skip_deleted_removed(
    subreddit: str = "AskReddit", posts: int = 1, comments: int = 15
) -> None:
    """
    Purpose:
      Confirm that deleted/removed/stickied comments are filtered out by reddit_client.
    What we check:
      - No printed comment lines should contain '[deleted]' or '[removed]'. We also do a simple scan to warn if any slipped through.
    """
    data = _fetch_with_comments(subreddit=subreddit, sort="top", requested=posts, comments=comments, time_filter="day")
    _print_posts_block(data, subreddit=subreddit, sort="top", time_filter="day", comments_to_show=comments)

    # Simple automated scan (best-effort; prints a warning if something is off)
    found_bad = 0
    for p in data:
        for c in p.get("comments", []):
            body = (c.get("body") or "").lower()
            if body in ("[deleted]", "[removed]"):
                found_bad += 1
    if found_bad == 0:
        print("[PASS] No deleted/removed comments printed.\n")
    else:
        print(f"[WARN] Found {found_bad} deleted/removed comments — check filtering.\n")

def test_deep_replies_formatting(
    subreddit: str = "AskReddit", posts: int = 1, comments: int = 15
) -> None:
    """
    Purpose:
      Make sure nested replies are flattened with 'depth' indentation and '(reply to …)' context.
    What we check:
      - At least one printed comment line has an arrow and a parent author.
    """
    data = _fetch_with_comments(subreddit=subreddit, sort="top", requested=posts, comments=comments, time_filter="day")
    _print_posts_block(data, subreddit=subreddit, sort="top", time_filter="day", comments_to_show=comments)

    nested = 0
    for p in data:
        for c in p.get("comments", []):
            if int(c.get("depth", 0) or 0) > 0 and c.get("parent_author"):
                nested += 1
    if nested > 0:
        print(f"[PASS] Found {nested} nested replies with parent context.\n")
    else:
        print("[WARN] No nested replies with parent context found in this sample.\n")

def test_min_score_threshold(
    subreddit: str = "MachineLearning", posts: int = 5, comments: int = 3
) -> None:
    """
    Purpose:
      Verify that min_score affects which posts pass the keep/skip gate and that
      over-fetching tries to compensate when a threshold is applied.
    What we check:
      - The number of returned posts with min_score=100 is <= the number with min_score=None.
    """
    none_data = _fetch_with_comments(subreddit=subreddit, sort="top", requested=posts, comments=comments, time_filter="day", min_score=None)
    high_data = _fetch_with_comments(subreddit=subreddit, sort="top", requested=posts, comments=comments, time_filter="day", min_score=100)
    _print_posts_block(none_data, subreddit=subreddit, sort="top", time_filter="day", comments_to_show=comments)
    _print_posts_block(high_data, subreddit=subreddit, sort="top", time_filter="day", comments_to_show=comments)
    print(f"[INFO] min_score=None -> {len(none_data)} posts; min_score=100 -> {len(high_data)} posts.\n")

def test_case_insensitive_subreddit(
    posts: int = 3, comments: int = 2
) -> None:
    """
    Purpose:
      The subreddit name should not be case-sensitive (PRAW handles this).
    What we check:
      - Fetching with 'ChatGPT' vs 'chatgpt' yields similar counts (and often overlapping IDs).
    """
    up = _fetch_with_comments(subreddit="ChatGPT", sort="top", requested=posts, comments=comments, time_filter="day")
    low = _fetch_with_comments(subreddit="chatgpt", sort="top", requested=posts, comments=comments, time_filter="day")
    _print_posts_block(up,  subreddit="ChatGPT", sort="top", time_filter="day", comments_to_show=comments)
    _print_posts_block(low, subreddit="chatgpt", sort="top", time_filter="day", comments_to_show=comments)
    up_ids = {p.get("id") for p in up}
    low_ids = {p.get("id") for p in low}
    overlap = len(up_ids & low_ids)
    print(f"[INFO] Case check: ChatGPT={len(up)}; chatgpt={len(low)}; overlap IDs={overlap}.\n")

def test_invalid_subreddit_behavior(
    subreddit: str = "thisSubDoesNotExist_____",
    posts: int = 2,
    comments: int = 2
) -> None:
    """
    Purpose:
      Basic resilience: calls should not crash the preview runner even for invalid subs.
    What we check:
      - We either get 0 items, or a readable exception message is printed here.
    """
    try:
        data = _fetch_with_comments(subreddit=subreddit, sort="top", requested=posts, comments=comments, time_filter="day")
        _print_posts_block(data, subreddit=subreddit, sort="top", time_filter="day", comments_to_show=comments)
        print(f"[INFO] Returned {len(data)} items for invalid subreddit name (this is OK if the API normalizes).\n")
    except Exception as e:
        print(f"[PASS] Caught exception gracefully for invalid subreddit: {e}\n")

def test_no_stickied_posts_in_results(
    subreddit: str = "MachineLearning", posts: int = 5, comments: int = 0
) -> None:
    """
    Purpose:
      Ensure stickied posts are excluded by our keep/skip gate.
    What we check:
      - None of the returned posts have 'stickied' == True.
    """
    data = _fetch_with_comments(subreddit=subreddit, sort="hot", requested=posts, comments=comments, time_filter="day")
    has_stickied = any(bool(p.get("stickied")) for p in data)
    _print_posts_block(data, subreddit=subreddit, sort="hot", time_filter=None, comments_to_show=comments)
    if not has_stickied:
        print("[PASS] No stickied posts present.\n")
    else:
        print("[WARN] Found a stickied post — check _is_valid_submission().\n")

# ============================ MAIN RUNNER ============================

def main() -> None:
    """
    Run a curated subset in a sensible order so the output is readable.
    You can comment/uncomment lines below depending on what you are investigating.
    """
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n===== Manual Preview Test Run — started {started} =====\n")

    # Coverage across sort types & windows
    test_top_day_texty_subreddit()
    test_top_day_vs_week_on_chatgpt()
    test_hot_basic()
    test_new_basic()

    # Parameters & filters
    test_comment_limit_variations()
    test_skip_deleted_removed()
    test_deep_replies_formatting()
    test_min_score_threshold()

    # Consistency & resilience
    test_case_insensitive_subreddit()
    test_invalid_subreddit_behavior()
    test_no_stickied_posts_in_results()

    finished = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n===== Manual Preview Test Run — finished {finished} =====\n")

if __name__ == "__main__":
    main()
