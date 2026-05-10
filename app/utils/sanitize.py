from markupsafe import escape


def clean_input(text, allow_html=False):
    """
    Robust input sanitization to prevent XSS and data injection.
    Escapes HTML special characters and normalizes whitespace.
    """
    if not text or not isinstance(text, str):
        return text

    # Remove null bytes and dangerous control characters
    text = text.replace('\0', '').strip()

    if not allow_html:
        # Standard HTML escaping for safety
        text = str(escape(text))

    return text
