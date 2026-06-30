"""Output encoding helpers.

Jinja2 autoescaping is ON by default for .html templates, which covers the
majority of XSS surface. These helpers handle edge cases where you build
strings outside of templates or need explicit control.
"""
import html

from markupsafe import Markup, escape


def nl2br(value) -> Markup:
    """Jinja filter: HTML-escape a value, then turn newlines into <br>.

    Escaping happens BEFORE the <br> substitution, so user-supplied markup
    (e.g. a profile address containing <script>) is rendered inert — only
    the <br> tags we insert are live. Safe to register as a Jinja filter.
    """
    if value is None:
        return Markup("")
    return escape(value).replace("\n", Markup("<br>\n"))


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
