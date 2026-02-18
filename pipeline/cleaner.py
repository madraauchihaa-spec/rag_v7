# pipeline/cleaner.py

import re

def remove_noise(content: str) -> str:

    # Remove excessive decorative table headers
    content = re.sub(r'\|\s*Sr\.?\s*No.*?\|', '', content, flags=re.IGNORECASE)

    # Remove Recommendation markers
    content = re.sub(r'Recommendation\s*---', '', content)

    # Remove excessive blank lines
    content = re.sub(r'\n\s*\n+', '\n\n', content)

    return content.strip()
