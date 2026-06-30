"""Output encoding helpers.

Jinja2 autoescaping is ON by default for .html templates, which covers the
majority of XSS surface. These helpers handle edge cases where you build
strings outside of templates or need explicit control.
"""
import html


def escape_html(value: str) -> str:
    """HTML-escape a string for safe insertion into HTML outside Jinja templates."""
    if not isinstance(value, str):
        value = str(value)
    return html.escape(value, quote=True)


def safe_display(value) -> str:
    """Convert any value to a display-safe string.
    Use in template filters or API responses where autoescaping is not active.
    """
    if value is None:
        return ""
    return html.escape(str(value), quote=True)
