"""
Unit tests for app/security/input_validation.py

Control under test: server-side input validation (length caps, email
format, non-empty fields, integer ranges, HTML-tag stripping). These are
pure functions, so no Flask app/client is needed.
"""
import pytest

from app.security.input_validation import (
    sanitize_text,
    validate_email,
    validate_non_empty,
    validate_length,
    validate_integer_range,
    strip_html,
    MAX_SHORT,
)


# -- sanitize_text -----------------------------------------------------

def test_sanitize_text_trims_and_truncates():
    assert sanitize_text("  hello  ") == "hello"
    assert sanitize_text("x" * 500, max_length=10) == "x" * 10


def test_sanitize_text_rejects_non_string_input():
    """Negative: non-string input (e.g. an int, list, or dict sent via a
    tampered request) degrades safely to an empty string instead of
    raising or being treated as valid."""
    assert sanitize_text(12345) == ""
    assert sanitize_text(None) == ""
    assert sanitize_text(["a", "b"]) == ""


# -- validate_email ------------------------------------------------------

@pytest.mark.parametrize(
    "email",
    ["user@example.com", "first.last@sub.example.co.uk", "a@b.io"],
)
def test_validate_email_accepts_well_formed_addresses(email):
    ok, error = validate_email(email)
    assert ok is True
    assert error is None


@pytest.mark.parametrize(
    "email",
    [
        "not-an-email",
        "missing-domain@",
        "@missing-local.com",
        "spaces in@example.com",
        "no-at-sign.example.com",
    ],
)
def test_validate_email_rejects_malformed_addresses(email):
    """Negative/abuse: malformed addresses are rejected with an error
    message, not silently accepted."""
    ok, error = validate_email(email)
    assert ok is False
    assert error is not None


# -- validate_non_empty --------------------------------------------------

def test_validate_non_empty_accepts_real_content():
    ok, error = validate_non_empty("hello", "Title")
    assert ok is True
    assert error is None


@pytest.mark.parametrize("value", ["", "   ", "\t\n", None])
def test_validate_non_empty_rejects_blank_or_whitespace(value):
    """Negative/abuse: blank or whitespace-only submissions are rejected,
    e.g. an attacker submitting a 'title' field of just spaces."""
    ok, error = validate_non_empty(value, "Title")
    assert ok is False
    assert "Title" in error


# -- validate_length ------------------------------------------------------

def test_validate_length_accepts_value_within_bounds():
    ok, error = validate_length("hello", "Field", min_len=1, max_len=10)
    assert ok is True
    assert error is None


def test_validate_length_rejects_too_short():
    ok, error = validate_length("", "Username", min_len=3, max_len=20)
    assert ok is False
    assert "at least" in error


def test_validate_length_rejects_too_long():
    """Negative/abuse: an oversized field (e.g. a buffer/DoS-style
    payload) is rejected rather than silently truncated."""
    ok, error = validate_length("x" * (MAX_SHORT + 1), "Field", max_len=MAX_SHORT)
    assert ok is False
    assert "at most" in error


# -- validate_integer_range -----------------------------------------------

def test_validate_integer_range_accepts_value_in_range():
    ok, error = validate_integer_range(5, "Quantity", min_val=1, max_val=10)
    assert ok is True
    assert error is None


@pytest.mark.parametrize("value", [0, -5, 9999999])
def test_validate_integer_range_rejects_out_of_range(value):
    """Negative/abuse: this is the control that should stop a tampered
    cart 'quantity' or 'price' field from going negative or absurdly
    large server-side, even if a client-side check was bypassed."""
    ok, error = validate_integer_range(value, "Quantity", min_val=1, max_val=100)
    assert ok is False
    assert "between" in error


@pytest.mark.parametrize("value", ["abc", None, "", [], {}])
def test_validate_integer_range_rejects_non_numeric_input(value):
    """Negative/abuse: a non-numeric tampered value must not raise an
    unhandled exception — it must fail validation cleanly."""
    ok, error = validate_integer_range(value, "Quantity")
    assert ok is False
    assert "whole number" in error


# -- strip_html ------------------------------------------------------------

def test_strip_html_removes_tags_and_keeps_text():
    result = strip_html("<b>Hello</b> <i>world</i>")
    assert result == "Hello world"


def test_strip_html_neutralizes_script_payload():
    """Negative/abuse: a free-text field fed a <script> XSS payload comes
    out as plain inert text, not as markup that could later be rendered
    unescaped."""
    payload = "<script>alert('xss')</script>Hi there"
    result = strip_html(payload)
    assert "<script>" not in result
    assert "Hi there" in result


def test_strip_html_enforces_max_length():
    result = strip_html("<p>" + ("y" * 5000) + "</p>", max_length=50)
    assert len(result) == 50