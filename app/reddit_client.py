import praw, praw.models, time
from typing import Optional, List, TypedDict, NotRequired
from .config import *

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

def _safe_text(s: Optional[str]) -> str:
    # Normalize None -> ""
    # (You could also strip or replace '\r\n' here if you want.)
    return s if isinstance(s, str) else ""

def create_reddit_client() -> praw.Reddit:
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )

def create_subreddit_client(subreddit: str) -> praw.models.Subreddit:
    reddit = create_reddit_client()
    return reddit.subreddit(subreddit)


def submission_to_postData(sub: praw.models.Submission) -> PostData:
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
def comment_to_commentdata(comm: praw.models.Comment) -> CommentData:
    data: CommentData = {
        "id": comm.id,
        "body": _safe_text(getattr(comm, "body", None)),
        "score": int(getattr(comm, "score", 0) or 0),
        "author": str(comm.author) if comm.author else "[deleted]",
    }
    return data

def _compute_fetch_limit(requested: int, min_score: int | None) -> int:
    if min_score is None:
        return requested
    return min(requested * OVER_FETCH_FACTOR, MAX_FETCH_POSTS)

def _iter_posts(sr: praw.models.Subreddit, sort: str="hot", limit: int=TOP_LIMIT, time_filter: str="day"):
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

def is_valid_submission(sub: praw.models.Submission) -> bool:
    # Filter out non-text/image posts, stickied posts, and very low-effort posts
    if getattr(sub, "stickied", False):
        return False
    else:
        # Link/image post: require a title
        if not sub.title or len(sub.title.strip()) < 10:
            return False
    return True

def get_hot_posts(
    subreddit: str,
    limit: int = TOP_LIMIT,
    min_score: Optional[int] = None,
                 ) -> List[PostData]:
    sr = create_subreddit_client(subreddit)
    fetch_limit = _compute_fetch_limit(limit, min_score)
    posts: List[PostData] = []
    for submission in _iter_posts(sr, sort="hot", limit=fetch_limit):
        post = submission_to_postData(submission)
        if min_score is not None and post["score"] < min_score:
            continue
        posts.append(post)
        if len(posts) >= limit:
            break
    return posts
def get_top_posts(
    subreddit: str,
    limit: int = TOP_LIMIT,
    time_filter: str = "day",
    min_score: Optional[int] = None,
                 ) -> List[PostData]:
    sr = create_subreddit_client(subreddit)
    fetch_limit = _compute_fetch_limit(limit, min_score)
    posts: List[PostData] = []
    for submission in _iter_posts(sr, sort="top", limit=fetch_limit, time_filter=time_filter):
        post = submission_to_postData(submission)
        if min_score is not None and post["score"] < min_score:
            continue
        posts.append(post)
        if len(posts) >= limit:
            break
    return posts





