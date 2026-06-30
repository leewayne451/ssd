import re
from html.parser import HTMLParser

# Maximum field lengths
MAX_SHORT = 100
MAX_LONG  = 2000


class _StripTagsParser(HTMLParser):
    """Minimal HTML parser that discards all tags and returns only text."""
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return "".join(self._parts)


def sanitize_text(value: str, max_length: int = MAX_SHORT) -> str:
    """Strip leading/trailing whitespace and enforce max length."""
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def validate_email(email: str) -> tuple[bool, str | None]:
    """Basic RFC-5322-ish email format check."""
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(pattern, email):
        return False, "Invalid email address."
    return True, None


def validate_non_empty(value: str, field_name: str = "Field") -> tuple[bool, str | None]:
    """Reject blank or whitespace-only strings."""
    if not value or not value.strip():
        return False, f"{field_name} cannot be empty."
    return True, None


def validate_length(
    value: str, field_name: str = "Field", min_len: int = 1, max_len: int = MAX_SHORT
) -> tuple[bool, str | None]:
    """Enforce min/max length on a string field."""
    if len(value) < min_len:
        return False, f"{field_name} must be at least {min_len} characters."
    if len(value) > max_len:
        return False, f"{field_name} must be at most {max_len} characters."
    return True, None


def validate_integer_range(
    value, field_name: str = "Value", min_val: int = 1, max_val: int = 9999
) -> tuple[bool, str | None]:
    """Validate that a value is an integer within an allowed range."""
    try:
        int_val = int(value)
    except (TypeError, ValueError):
        return False, f"{field_name} must be a whole number."
    if not (min_val <= int_val <= max_val):
        return False, f"{field_name} must be between {min_val} and {max_val}."
    return True, None


def strip_html(value: str, max_length: int = MAX_LONG) -> str:
    """Remove all HTML tags using stdlib html.parser and enforce max length.
    Use this for any free-text field that must never render HTML.
    No third-party dependency required. Non-string input (e.g. a missing
    optional form field arriving as None) degrades safely to "".
    """
    if not isinstance(value, str):
        return ""
    parser = _StripTagsParser()
    parser.feed(value)
    return parser.get_text().strip()[:max_length]