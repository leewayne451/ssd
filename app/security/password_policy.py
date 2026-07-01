import re
from zxcvbn import zxcvbn

def validate_password(password: str) -> tuple[bool, str | None]:
    # 1. Length check (zxcvbn also checks this, but we keep our own)
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    
    # 2. Complexity checks (uppercase, lowercase, digit, special)
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit."
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:\'",.<>?/~`]', password):
        return False, "Password must contain at least one special character."

    # 3. The zxcvbn check (covers common passwords, patterns, dictionary words)
    result = zxcvbn(password)
    
    # Score is 0 (very weak) to 4 (very strong). 
    # We require at least a score of 3 (strong) to block 'password123' and similar.
    if result['score'] < 3:
        # feedback contains a helpful suggestion for the user
        feedback = result['feedback']['warning']
        if feedback:
            return False, feedback
        # If no specific warning, give a generic message.
        return False, "Password is too weak. Try a longer phrase with varied characters."

    return True, None