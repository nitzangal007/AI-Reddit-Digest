import praw, praw.models, time
from typing import Optional, List, TypedDict, NotRequired
from .config import *
from typing import Literal

Sort = Literal["hot", "new", "top"]
TopWindow = Literal["hour","day","week","month","year","all"]

class CommentData(TypedDict):
    id: str
    body: str
    score: int
    author: str
    created_utc: NotRequired[float]

    # Context to avoid confusion when showing replies in a flat list:
    depth: NotRequired[int]          # 0 for top-level, 1 for a reply, etc.
    is_top_level: NotRequired[bool]  # True if depth == 0
    parent_id: NotRequired[str]      # e.g., "t3_<postid>" or "t1_<commentid>"
    parent_author: NotRequired[str]  # username of the parent comment’s author

class PostData(TypedDict):
    id: str
    title: str
    score: int
    url: str
    selftext: str
    created_utc: float
    author: str
    num_comments: int
    permalink: str
    stickied: NotRequired[bool]
    comments: list[CommentData]  # List of comments

"""Normalize possibly-None text fields from PRAW to a safe string."""
def _safe_text(s: Optional[str]) -> str:
    return s if isinstance(s, str) else ""

"""Construct an authenticated PRAW client using env/config settings."""
def create_reddit_client() -> praw.Reddit:
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )

"""Return a Subreddit handle"""
def create_subreddit_client(subreddit: str) -> praw.models.Subreddit:
    reddit = create_reddit_client()
    return reddit.subreddit(subreddit)

"""Normalize a PRAW Submission into our stable PostData shape."""
def submission_to_post_data(sub: praw.models.Submission) -> PostData:
    data: PostData = {
        "id": sub.id,
        "title": _safe_text(sub.title),
        "score": int(sub.score or 0),
        "url": _safe_text(sub.url),
        "selftext": _safe_text(sub.selftext),
        "created_utc": float(sub.created_utc or 0.0),
        "author": str(sub.author) if sub.author else "[deleted]",
        "num_comments": int(sub.num_comments or 0),
        "permalink": f"https://reddit.com{sub.permalink}",
        "stickied": bool(getattr(sub, "stickied", False)),
        "comments": [],  # required by PostData; fill later if needed
    }
    return data

"""Normalize a PRAW Comment into our CommentData base."""
def comment_to_comment_data(comm: praw.models.Comment) -> CommentData:
    data: CommentData = {
        "id": comm.id,
        "body": _safe_text(getattr(comm, "body", None)),
        "score": int(getattr(comm, "score", 0) or 0),
        "author": str(comm.author) if comm.author else "[deleted]",
    }
    return data

"""Compute how many posts to fetch from Reddit to have a good chance of getting `requested`"""
def _compute_fetch_limit(requested: int, min_score: int | None) -> int:
    if min_score is None:
        return requested
    return min(requested * OVER_FETCH_FACTOR, MAX_FETCH_POSTS)

"""Yield up to `limit` posts from the subreddit `sr`, sorted by `sort`."""
def _iter_posts(sr: praw.models.Subreddit, sort: Sort="hot", limit: int=TOP_LIMIT, time_filter: TopWindow="day"):
    if sort == "hot":
        listing = sr.hot(limit=limit)
    elif sort == "top":
        listing = sr.top(time_filter=time_filter, limit=limit)
    elif sort == "new":
        listing = sr.new(limit=limit)
    else:
        raise ValueError(f"Unsupported sort: {sort}")

    for submission in listing:  # PRAW iterable
        yield submission

"""Single keep/skip gate for posts (stickies, score, title length, text-only by default)."""
def _is_valid_submission(
    sub: praw.models.Submission,
    *,
    min_score: int | None = None,
    allow_stickied: bool = False,
    min_title_len: int = 10,
    only_text_posts: bool = True,   # NEW
    ) -> bool:
    if getattr(sub, "stickied", False) and not allow_stickied:
        return False
    if min_score is not None and int(getattr(sub, "score", 0) or 0) < min_score:
        return False
    if len((getattr(sub, "title", "") or "").strip()) < min_title_len:
        return False
    if only_text_posts:
        # require self-post or non-empty selftext
        if not bool(getattr(sub, "is_self", False)):
            return False
    return True

"""Single keep/skip gate for comments (deleted/removed, score, stickied)."""
def _is_valid_comment(
    c: praw.models.Comment,
    *,
    min_score: int | None = None,
    skip_stickied: bool = True,
    ) -> bool:
    if skip_stickied and bool(getattr(c, "stickied", False)):
        return False
    body = (getattr(c, "body", "") or "").strip()
    if body.lower() in ("[deleted]", "[removed]") or not body:
        return False
    if min_score is not None and int(getattr(c, "score", 0) or 0) < min_score:
        return False
    return True

"""Return up to `requested` normalized posts for the chosen sort."""
def get_posts(
    subreddit: str,
    *,
    sort: Sort = "hot",
    requested: int = 5,
    min_score: int | None = None,
    time_filter: TopWindow = "day",
) -> list[PostData]:
    sr = create_subreddit_client(subreddit)
    limit = _compute_fetch_limit(requested, min_score)
    out: list[PostData] = []

    for sub in _iter_posts(sr, sort=sort, limit=limit, time_filter=time_filter):
        if not _is_valid_submission(sub, min_score=min_score, allow_stickied=False, min_title_len=10, only_text_posts=True):
            continue
        # Passed all filters; include it
        out.append(submission_to_post_data(sub))
        if len(out) >= requested:
            break
    return out

"""Ergonomic wrapper around `get_posts` or `get_posts_with_comments` for hot listing."""
def get_hot_posts(
    subreddit: str,
    limit: int = TOP_LIMIT,
    min_score: int | None = None,
    with_comments: bool = False,
                 ) -> List[PostData]:
    if with_comments:
        return get_posts_with_comments(subreddit, sort="hot", requested=limit, min_score=min_score, comment_limit=DEFAULT_COMMENT_LIMIT)
    else:
        return get_posts(subreddit, sort="hot", requested=limit, min_score=min_score)

"""Ergonomic wrapper around `get_posts` or `get_posts_with_comments` for top listing."""
def get_top_posts(
    subreddit: str,
    limit: int = TOP_LIMIT,
    time_filter: TopWindow = "day",
    min_score: int = 100,
    with_comments: bool = False,
                 ) -> List[PostData]:
    if with_comments:
        return get_posts_with_comments(subreddit, sort="top", requested=limit, time_filter=time_filter, min_score=min_score, comment_limit=DEFAULT_COMMENT_LIMIT)
    else:
        return get_posts(subreddit, sort="top", requested=limit, time_filter=time_filter, min_score=min_score)

"""Ergonomic wrapper around `get_posts` or `get_posts_with_comments` for new listing."""
def get_new_posts(
    subreddit: str,
    limit: int = TOP_LIMIT,
    min_score: int | None = None,
    with_comments: bool = False,
                 ) -> List[PostData]:
    if with_comments:
        return get_posts_with_comments(subreddit, sort="new", requested=limit, min_score=min_score, comment_limit=DEFAULT_COMMENT_LIMIT)
    else:
        return get_posts(subreddit, sort="new", requested=limit, min_score=min_score)

"""Walk a comment forest (list of top-level comments) in DFS order, returning a flat list with context."""
def _walk_thread_flat_with_context(cforest, limit: int) -> list[CommentData]:
    out: list[CommentData] = []

    """Visit a comment and its replies recursively, adding valid ones to `out`."""
    def visit(c: praw.models.Comment, depth: int, parent_author: str | None):
        if len(out) >= limit:
            return
        author_name = str(getattr(c, "author", None)) if getattr(c, "author", None) else "[deleted]"
        if _is_valid_comment(c, min_score=None, skip_stickied=True):
            node = comment_to_comment_data(c)
            node["depth"] = depth
            node["is_top_level"] = (depth == 0)
            if getattr(c, "parent_id", None):
                node["parent_id"] = c.parent_id
            if parent_author:
                node["parent_author"] = parent_author

            out.append(node)

        # Recurse into replies (children)
        for r in getattr(c, "replies", []):
            if len(out) >= limit:
                break
            if isinstance(r, praw.models.Comment):
                visit(r, depth + 1, author_name)

    # Start with each top-level comment
    for top in cforest:
        if len(out) >= limit:
            break
        if isinstance(top, praw.models.Comment):
            visit(top, depth=0, parent_author=None)

    return out

"""Fetch up to `comment_limit` comments for the submission `sub`, in a flat list with context."""
def fetch_comments_flat_with_context(sub: praw.models.Submission,
                                     comment_limit: int=10,
                                     sort: Sort="top")-> List[CommentData]:
    sub.comment_sort = sort
    sub.comments.replace_more(limit=0)
    return _walk_thread_flat_with_context(sub.comments, comment_limit)



"""High-level bundler: fetch posts, filter/normalize, then attach up to `comment_limit` comments per post.
      Comments are fetched only for accepted posts to avoid wasted API calls."""
    # 1) compute over-fetch limit
    # 2) iterate submissions via _iter_posts
    # 3) apply _is_valid_submission; then normalize
    # 4) fetch comments with comment_sort='top' (don’t reuse post sort); attach; early-break on count
def get_posts_with_comments(
    subreddit: str,
    *,
    sort: Sort = "hot",
    requested: int = 5,
    comment_limit: int = 10,
    min_score: int | None = None,
    time_filter: TopWindow = "day",) -> list[PostData]:
    sr = create_subreddit_client(subreddit)
    limit = _compute_fetch_limit(requested, min_score)
    out: list[PostData] = []
    for sub in _iter_posts(sr, sort=sort, limit=limit, time_filter=time_filter):
        if not _is_valid_submission(sub, min_score=min_score, allow_stickied=False, min_title_len=10, only_text_posts=True):
            continue
        post=submission_to_post_data(sub)
        comment=fetch_comments_flat_with_context(sub, comment_limit=comment_limit, sort="top")
        post["comments"]=comment
        out.append(post)
        if len(out) >= requested:
            break
    return out








