def summarize_text(text: str) -> str:
    """Very simple MVP summarizer: truncate to 140 chars.
    Replace later with real AI summarization.        """
    text = text or ""
    return (text[:140] + "...") if len(text) > 140 else text
