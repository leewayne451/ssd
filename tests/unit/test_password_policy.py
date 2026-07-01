import pytest
from app.security.password_policy import validate_password


# ------------------------------------------------------------
# 1. Length and complexity checks (hard requirements)
# ------------------------------------------------------------
def test_password_too_short():
    """Test that passwords under 8 characters are rejected."""
    is_valid, error = validate_password("Ab1!")
    assert is_valid is False
    assert "at least 8 characters" in error


def test_password_missing_uppercase():
    """Test that passwords without uppercase letters are rejected."""
    is_valid, error = validate_password("lowercase123!")
    assert is_valid is False
    assert "uppercase" in error


def test_password_missing_lowercase():
    """Test that passwords without lowercase letters are rejected."""
    is_valid, error = validate_password("UPPERCASE123!")
    assert is_valid is False
    assert "lowercase" in error


def test_password_missing_digit():
    """Test that passwords without digits are rejected."""
    is_valid, error = validate_password("NoDigitsHere!")
    assert is_valid is False
    assert "digit" in error


def test_password_missing_special():
    """Test that passwords without special characters are rejected."""
    is_valid, error = validate_password("NoSpecial123")
    assert is_valid is False
    assert "special character" in error


# ------------------------------------------------------------
# 2. zxcvbn strength checks (common / weak patterns)
#    These passwords must meet length/complexity requirements
#    but are still considered weak by zxcvbn.
# ------------------------------------------------------------
@pytest.mark.parametrize("weak_password", [
    "P@ssw0rd",          # Leetspeak substitution
    "Password123!",      # Common with uppercase + numbers + special
    "Qwerty123!",        # Keyboard pattern
    "Letmein123!",       # Common phrase
])
def test_password_common_or_weak(weak_password):
    """
    Test that passwords which meet complexity but are flagged by zxcvbn
    as common/weak are rejected.
    """
    is_valid, error = validate_password(weak_password)
    assert is_valid is False
    assert error is not None
    # The error message should mention weakness, commonness, or pattern
    assert any(keyword in error.lower() for keyword in ['common', 'weak', 'similar', 'guess'])


# ------------------------------------------------------------
# 3. Strong passwords (should pass)
# ------------------------------------------------------------
@pytest.mark.parametrize("strong_password", [
    "MyC0mpl3x$ecureP@ss!",
    "Correct-Horse-Battery-Staple!42",  # Added a digit
    "BlueBanana$42Rocket",
    "Tr0ub4dor&3",
])
def test_password_strong_passes(strong_password):
    """Test that genuinely strong passwords pass validation."""
    is_valid, error = validate_password(strong_password)
    assert is_valid is True
    assert error is None