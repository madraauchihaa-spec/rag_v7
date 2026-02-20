# act_pipeline/pipeline/act_cleaner.py

import re


def clean_act(content: str) -> str:
    """
    Production-grade legal cleaner.
    Removes editorial noise while preserving statutory structure.
    """

    # Remove standalone page numbers
    content = re.sub(r'\n\s*\d+\s*\n', '\n', content)

    # Remove amendment footnotes like:
    # 1. Subs. by Act 94 of 1976...
    content = re.sub(
        r'\n\d+\.\s+(Subs\.|Ins\.|Omitted|Added|Rep\.).*',
        '',
        content
    )

    # Remove superscript references like 1[...]
    content = re.sub(r'\d+\[.*?\]', '', content)

    # Remove superscript numerals
    content = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]', '', content)

    # Normalize STATE AMENDMENT headers
    content = re.sub(
        r'##\s*STATE\s+AMENDMENTS?',
        'STATE_AMENDMENTS_SECTION',
        content,
        flags=re.IGNORECASE
    )

    # Normalize Maharashtra Amendment headers
    content = re.sub(
        r'##\s*Maharashtra.*',
        'STATE_AMENDMENT_MARKER',
        content,
        flags=re.IGNORECASE
    )

    # Normalize blank lines
    content = re.sub(r'\n\s*\n+', '\n\n', content)

    return content.strip()
