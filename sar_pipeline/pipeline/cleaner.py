# pipeline/cleaner.py

import re


def remove_noise(content: str) -> str:

    # Remove decorative Sr No header rows
    content = re.sub(r'\|\s*Sr\.?\s*No.*?\|', '', content, flags=re.IGNORECASE)

    # Remove recommendation markers
    content = re.sub(r'Recommendations?\s*---', '', content, flags=re.IGNORECASE)

    # Remove excessive table separators
    content = re.sub(r'\|\s*[-]+\s*\|', '', content)

    # Normalize blank lines
    content = re.sub(r'\n\s*\n+', '\n\n', content)

    return content.strip()
