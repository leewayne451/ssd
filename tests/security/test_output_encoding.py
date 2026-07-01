"""
Unit tests for app/security/output_encoding.py

Control under test: explicit HTML-escaping for any value rendered outside
Jinja's auto-escaping (e.g. building strings manually, or returning data
in a non-template API response). This is the XSS-defence control.
"""
from app.security.output_encoding import escape_html, safe_display


# -- escape_html -----------------------------------------------------------

def test_escape_html_escapes_script_tag():
    """Negative/abuse: a classic <script> XSS payload must come back with
    no raw '<script>' substring — it must be fully entity-encoded."""
    payload = "<script>alert('xss')</script>"
    result = escape_html(payload)

    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_escape_html_escapes_quotes_for_attribute_context():
    """Positive: quote=True means values are also safe to drop into an
    HTML attribute (e.g. value=\"...\"), not just element text — this
    blocks attribute-breakout XSS like `"><img onerror=...>`."""
    payload = '"><img src=x onerror=alert(1)>'
    result = escape_html(payload)

    assert '"' not in result
    assert "&quot;" in result


def test_escape_html_passes_through_plain_text_unchanged_in_meaning():
    assert escape_html("Hello world") == "Hello world"


def test_escape_html_coerces_non_string_input():
    """Positive: non-string input (e.g. an int from a model field) is
    coerced to text rather than raising, so callers don't need to
    str()-guard every call site."""
    assert escape_html(42) == "42"


# -- safe_display -----------------------------------------------------------

def test_safe_display_returns_empty_string_for_none():
    """Negative edge case: a None field (e.g. an optional profile bio)
    renders as an empty string rather than the literal text 'None'."""
    assert safe_display(None) == ""


def test_safe_display_escapes_xss_payload():
    payload = "<img src=x onerror=alert(document.cookie)>"
    result = safe_display(payload)
    assert "<img" not in result
    assert "&lt;img" in result


def test_safe_display_handles_numeric_and_boolean_values():
    assert safe_display(7) == "7"
    assert safe_display(True) == "True"