# app/utils/text_cleaner.py
import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Cleans raw extracted text for embedding and storage.
    - Normalizes unicode characters
    - Removes excessive whitespace and newlines
    - Strips non-printable / control characters
    - Collapses multiple spaces into one
    """
    if not text or not isinstance(text, str):
        return ""

    # Normalize unicode (e.g. ligatures, accented chars)
    text = unicodedata.normalize("NFKC", text)

    # Remove control/non-printable characters (except newline/tab)
    text = re.sub(r"[^\x09\x0A\x20-\x7E\u00A0-\uFFFF]", " ", text)

    # Replace multiple newlines with a single one
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Collapse multiple spaces into one
    text = re.sub(r" {2,}", " ", text)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)

    return text.strip()


def truncate_text(text: str, max_chars: int = 2000) -> str:
    """
    Truncates text to a max character limit without cutting mid-word.
    """
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    return (truncated[:last_space] if last_space > 0 else truncated) + "..."


def normalize_whitespace(text: str) -> str:
    """
    Collapses all whitespace (spaces, newlines, tabs) into a single space.
    Useful for single-line embedding contexts.
    """
    return re.sub(r"\s+", " ", text).strip()
