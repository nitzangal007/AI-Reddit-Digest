import praw
from .config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

def create_reddit_client() -> praw.Reddit:
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )

def create_subreddit_client(subreddit: str) -> praw.models.Subreddit:
    reddit = create_reddit_client()
    return reddit.subreddit(subreddit)

def top_posts(subreddit: str, limit: int = 5, min_score: int = 0, time_filter: str = "day"):
    reddit = create_reddit_client()
    sr = reddit.subreddit(subreddit)
    yielded = 0
    for post in sr.top(limit=limit*5, time_filter=time_filter):
        if post.stickied or post.score < min_score:
            continue
        yield {
            "id": post.id,
            "title": post.title or "",
            "score": int(post.score),
            "url": post.url or "",
            "selftext": post.selftext or "",
        }
        yielded += 1
        if yielded >= limit:
            break

def hot_posts(subreddit: str, limit: int = 5, min_score: int | None = None):
    reddit = create_reddit_client()
    sr = reddit.subreddit(subreddit)

    # אם יש סף ניקוד — נביא יותר כדי שלא "ייגמרו" לנו אחרי הסינון
    fetch_limit = limit * 5 if min_score is not None else limit
    yielded = 0

    for post in sr.hot(limit=fetch_limit):
        if post.stickied:
            continue  # מדלגים על פוסטים מוצמדים
        if (min_score is None) or (post.score >= min_score):
            yield {
                "id": post.id,
                "title": post.title or "",
                "score": int(post.score),
                "url": post.url or "",
                "selftext": post.selftext or "",
            }
            yielded += 1
            if yielded >= limit:
                break
def hot_post_and_comments(subreddit: str, limit: int = 5, comment_limit: int = 3):
    reddit = create_reddit_client()
    sr = reddit.subreddit(subreddit)
    yielded = 0
    for post in sr.hot(limit=limit*5):
        if post.stickied:
            continue
        post.comments.replace_more(limit=0)
        comments = [comment.body for comment in post.comments.list()[:comment_limit]]
        yield {
            "id": post.id,
            "title": post.title or "",
            "score": int(post.score),
            "url": post.url or "",
            "selftext": post.selftext or "",
            "comments": comments,
        }
        yielded += 1
        if yielded >= limit:
            break