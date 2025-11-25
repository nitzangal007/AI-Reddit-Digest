import math
import re
import html
import unicodedata
from app.config import STOPWORDS
from math import log2
from collections import defaultdict, Counter
from heapq import nlargest
from typing import List, Dict, Set, Optional, Tuple, Iterable, Any
from dataclasses import dataclass


RE_MD_LINK = re.compile(r"\[([^\]]+)\]\((?:https?://|www\.)[^)]+\)", re.IGNORECASE)
RE_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
RE_USER_SUBR = re.compile(r"\b[ur]/([A-Za-z0-9_]+)\b")  # keep the name, drop the prefix
RE_CODE_TICKS = re.compile(r"`+")
RE_BLOCK_QUOTE = re.compile(r"(?m)^\s*>\s?")            # remove leading '>' quote markers
RE_NON_WORD_EXCEPT_SPACE = re.compile(r"[^\w\s]+", re.UNICODE)  # keep all Unicode letters/digits + space
RE_UNDERSCORE = re.compile(r"_+")
RE_WS = re.compile(r"\s+")

def summarize_text(text: str) -> str:
    """Very simple MVP summarizer: truncate to 340 chars.
    Replace later with real AI summarization.        """
    text = text or ""
    return (text[:340] + "...") if len(text) > 340 else text

def normalize_text(text: str) -> str:
    """Clean Reddit comment text (Unicode-safe), preserving human words and link labels."""
    if not text:
        return ""

    # 1) Decode entities & normalize Unicode, then lowercase
    s = html.unescape(text)
    s = unicodedata.normalize("NFKC", s).lower()

    # 2) Markdown links: keep the label, drop the URL part
    #    Example: "[proof](https://example.com)" -> "proof"
    s = RE_MD_LINK.sub(r"\1", s)

    # 3) Remove bare URLs (after extracting labels so they aren't lost)
    s = RE_URL.sub(" ", s)

    # 4) Reddit mentions: keep the name, drop the "u/" or "r/" prefix
    #    "u/AutoModerator" -> "automoderator", "r/ChatGPT" -> "chatgpt"
    s = RE_USER_SUBR.sub(r"\1", s)

    # 5) Drop code backticks and leading blockquote markers
    s = RE_CODE_TICKS.sub("", s)
    s = RE_BLOCK_QUOTE.sub("", s)

    # 6) Remove punctuation/symbols but KEEP Unicode letters/digits and spaces
    #    (This preserves Hebrew/Arabic/etc. instead of stripping them.)
    s = RE_NON_WORD_EXCEPT_SPACE.sub(" ", s)

    # 7) Convert underscores to spaces, collapse whitespace
    s = RE_UNDERSCORE.sub(" ", s)
    s = RE_WS.sub(" ", s).strip()

    return s

def cheap_stem(token: str) -> str:
    """
    Cheap, heuristic stemmer for de-dup/clustering (English-biased, Unicode-safe).
    Tries to avoid over-stemming while handling common endings.
    """
    t = token
    if not t or len(t) <= 3 or t.isdigit():
        return t

    # 1) Plurals
    if t.endswith("ies"):
        # studies -> study, stories -> story
        return t[:-3] + "y"

    # Only strip 'es' for sibilant plurals; avoid 'cases' -> 'cas'
    if t.endswith(("ches", "shes", "xes", "zes", "sses")):
        # watches -> watch, dishes -> dish, boxes -> box, buzzes -> buzz, dresses -> dress
        return t[:-2]

    if t.endswith("s") and not t.endswith("ss"):
        # cats -> cat, but keep 'boss'
        return t[:-1]

    # 2) Verb/adverb endings, with light safeguards
    # Un-doubling table (running -> run, shopping -> shop, stopped -> stop)
    _double_cons = {"bb","dd","ff","gg","ll","mm","nn","pp","rr","ss","tt","zz"}

    if t.endswith("ing") and len(t) >= 6:
        base = t[:-3]
        if len(base) >= 2 and base[-2:] in _double_cons:
            base = base[:-1]
        return base

    if t.endswith("ed") and len(t) >= 5:
        base = t[:-2]
        if len(base) >= 2 and base[-2:] in _double_cons:
            base = base[:-1]
        return base

    if t.endswith("ly") and len(t) > 4:
        return t[:-2]

    return t


def tokenize(text: str) -> list[str]:
    """split text into words, removing punctuation and lowercasing."""
    if not text:
        return []
    norm = normalize_text(text)
    tokens = RE_WS.split(norm)
    tokens = [t for t in tokens if t and t not in STOPWORDS and (len(t) > 1 or  t.isdigit())]
    return tokens


def tokenset(text: str) -> set[str]:
    """produce a set of unique, stemmed tokens for similarity comparisons"""
    tokens = tokenize(text)
    stemmed = [cheap_stem(t) for t in tokens]
    return set(stemmed)

def detect_bot_author(name: Optional[str]) -> bool:
    """Heuristic bot detector: True for AutoModerator or names starting/ending with 'bot'."""
    if not name:
        return True
    n = name.strip().lower()
    if n == "automoderator":
        return True
    if n.endswith("bot") or n.startswith("bot"):
        return True
    return False

def length_multiplier(norm_len: int) -> float:
    """Light length prior: reward medium posts, nudge very short/very long."""
    if norm_len < 5:
        return 0.9
    if norm_len <= 60:
        return 1.1
    if norm_len <= 120:
        return 1.0
    return 0.9

def score_comment(score: int, depth: int, body: str, author: Optional[str]) -> float:
    """
    Compute an importance weight for a comment:
      - Upvotes (log-scaled)
      - Depth penalty (top-level > replies)
      - Length prior (medium length is best)
      - Bot/automod penalty
    """
    if not body:
        return 0.0

    b = body.strip().lower()
    if b in ("[deleted]", "[removed]"):
        return 0.0

    # Tokenize (this calls normalize_text inside your tokenize())
    # If you already have a normalized body upstream, you can pass tokens in to avoid double work.
    tokens = tokenize(body)
    norm_len = len(tokens)

    base = math.log2(1 + max(score, 0))
    depth_factor = 1.0 / (1 + max(depth, 0))
    length_factor = length_multiplier(norm_len)
    author_factor = 0.85 if detect_bot_author(author) else 1.0

    # Small floor so non-zero-score, decent replies don't vanish entirely
    base = max(base, 0.25)

    return base * depth_factor * length_factor * author_factor

def split_into_sentences(text: str) -> List[str]:
    """Very naive sentence splitter based on punctuation."""
    if not text:
        return []
    parts = re.split(r'(?<=[.!?...])\s+|\n+', text.strip())
    sentences = [p.strip() for p in parts if p.strip()]
    sents = [s for s in sentences if len(tokenize(s)) >= 4]
    return sents

def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

def score_sentence(sentence: str, title: str, idx: int) -> float:
    """Score a sentence for summary inclusion based on:
       - Overlap with title (Jaccard similarity)
       - Position in text (earlier is better)
       - Length prior (medium length is best)
    """
    if not sentence:
        return 0.0
    tokens = tokenset(sentence)
    title_tokens = tokenset(title)
    title_overlap = jaccard_similarity(tokens, title_tokens)
    position_factor = 1.0 / (1 + idx)  # earlier sentences get
    length_factor = length_multiplier(len(tokenize(sentence)))
    return 0.5 * title_overlap + 0.3 * position_factor + 0.2 * length_factor

def trim_smart(text: str, max_chars: int) -> str:
    """Trim text to max_chars without cutting words if possible, adding ellipsis."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rstrip()
    space = cut.rfind(" ")
    if space == -1 or (len(cut) - space) > 20:
        return cut + "…"
    return cut[:space] + "…"

def pick_top_nonredundant(scored_sents, k=3, sim_thresh=0.6, max_chars=320) -> str:
    """Pick top-k non-redundant sentences based on scores and similarity threshold."""
    if not scored_sents:
        return ""

    # Sort by score descending
    scored_sents.sort(key=lambda x: x[1], reverse=True)

    selected = []
    selected_sets = []

    for sent, score in scored_sents:
        if len(selected) >= k:
            break
        sent_set = tokenset(sent)
        if any(jaccard_similarity(sent_set, s) >= sim_thresh for s in selected_sets):
            continue  # too similar to existing
        selected.append(sent)
        selected_sets.append(sent_set)
    out=" ".join(selected)
    out=trim_smart(out, max_chars)
    return out

def summarize_post(title: str, selftext: str, max_char:int = 320) -> str:
    """Summarize a Reddit post (title + selftext) into a concise summary."""
    body_sents = split_into_sentences(selftext)
    if not body_sents:
        doc = f"{title}\n\n{selftext}".strip()
        return trim_smart(doc, max_char)
    scored_sents = [(s, score_sentence(s, title, i)) for i, s in enumerate(body_sents)]
    best = pick_top_nonredundant(scored_sents, k=3, sim_thresh=0.6, max_chars=max_char)
    if not best:
        doc = f"{title}\n\n{selftext}".strip()
        return trim_smart(doc, max_char)
    return best




