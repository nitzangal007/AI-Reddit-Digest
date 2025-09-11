def summarize_text(text: str) -> str:
    """Very simple MVP summarizer: truncate to 340 chars.
    Replace later with real AI summarization.        """
    text = text or ""
    return (text[:340] + "...") if len(text) > 340 else text
