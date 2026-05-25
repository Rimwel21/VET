def clean_input(text, allow_html=False):
    """
    Robust input sanitization to prevent XSS and data injection.
    Escapes HTML special characters and normalizes whitespace.
    """
    from app.utils.validation import sanitize_text

    if text is None:
        return text

    return sanitize_text(text, allow_newlines=False, escape_html=not allow_html)
