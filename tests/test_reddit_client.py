from typing import Optional
from app import reddit_client as rc

def test_create_reddit_client():
    client = rc.create_reddit_client()
    assert client is not None
    # Add more assertions as needed

def test_safe_text():
    assert rc._safe_text(None) == ""
    assert rc._safe_text("hi") == "hi"

def test_compute_fetch_limit():
    # Without min_score, should return requested
    assert rc._compute_fetch_limit(5, None) == 5
    # With min_score, should over-fetch but cap
    lim = rc._compute_fetch_limit(5, 100)
    assert 5 < lim <= 200

def test_is_valid_submission_basic():
    # Minimal fake Submission with only attrs we read
    class FakeSub:
        def __init__(
            self,
            *,
            title: str = "A valid enough title",
            score: int = 123,
            stickied: bool = False,
            removed_by_category: Optional[str] = None,
            over_18: bool = False,
        ):
            self.title = title
            self.score = score
            self.stickied = stickied
            self.removed_by_category = removed_by_category
            self.over_18 = over_18

    keep = FakeSub()
    drop_sticky = FakeSub(stickied=True)
    drop_short_title = FakeSub(title="short")

    # Your project might name the function `_is_valid_submission` or `is_valid_submission`
    is_valid = getattr(rc, "_is_valid_submission", getattr(rc, "_is_valid_submission"))

    assert is_valid(keep, min_score=None, allow_stickied=False, min_title_len=10)
    assert not is_valid(drop_sticky, min_score=None, allow_stickied=False, min_title_len=10)
    assert not is_valid(drop_short_title, min_score=None, allow_stickied=False, min_title_len=10)

def test_get_hot_posts_filters(monkeypatch):

    class FakeCommentsList(list):
        def replace_more(self, limit=0): return
        def list(self): return list(self)

    class FakeSubmission:
        def __init__(self, id, title, score, url, stickied=False, comments=None):
            self.id = id
            self.title = title
            self.score = score
            self.url = url
            self.stickied = stickied
            self.permalink = f"/r/testsub/comments/{id}"
            self.num_comments = len(comments or [])
            self.comments = comments or FakeCommentsList()
            # extra attrs used by submission_to_post_data:
            self.selftext = ""
            self.created_utc = 0.0
            self.author = "alice"

    class FakeSubreddit:
        def __init__(self, display_name, submissions):
            self.display_name = display_name
            self._submissions = submissions
        def hot(self, limit=None):
            # honor limit like PRAW
            return iter(self._submissions if limit is None else self._submissions[:limit])

    stickied = FakeSubmission("p0", "Stickied announcement 12345", score=999, url="http://x/0", stickied=True)
    s1       = FakeSubmission("p1", "A good post title 12345",     score=50,  url="http://x/1")
    s2       = FakeSubmission("p2", "A low score post 12345",      score=2,   url="http://x/2")

    fake_sr = FakeSubreddit("testsub", [stickied, s1, s2])

    # Route code under test to our fake subreddit
    monkeypatch.setattr(rc, "create_subreddit_client", lambda name: fake_sr)

    # Act: ask for 1 post but set a min_score to trigger over-fetching (so we can skip the sticky and still get s1)
    posts = rc.get_hot_posts("testsub", limit=1, min_score=5)

    # Assert: exactly one post, it’s p1; sticky and low-score are not returned
    assert len(posts) == 1
    ids = [p["id"] for p in posts]
    assert ids == ["p1"]
    # sanity on normalized fields
    assert posts[0]["comments"] == []     # your normalizer always sets comments
    assert posts[0]["permalink"].startswith("https://reddit.com")