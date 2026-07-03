"""Redaction of secret-shaped strings (all fixtures are fake values)."""

from tools.ai_review.redaction import contains_secret, redact


class TestRedaction:
    def test_fake_openai_key_redacted(self):
        text = "OPENAI_API_KEY = 'sk-proj-abcdefghijklmnop1234567890ABCD'"
        result = redact(text)
        assert "sk-proj-" not in result
        assert "REDACTED" in result

    def test_fake_openai_key_plain_prefix(self):
        assert "sk-test" not in redact("key=sk-testabcdefghijklmnop123456")

    def test_fake_aws_access_key_redacted(self):
        result = redact("aws_access_key_id = AKIAIOSFODNN7EXAMPLE")
        assert "AKIAIOSFODNN7EXAMPLE" not in result

    def test_fake_aws_secret_key_redacted(self):
        result = redact(
            "aws_secret_access_key = wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY"
        )
        assert "wJalrXUtnFEMI" not in result

    def test_fake_github_token_redacted(self):
        result = redact("token: ghp_abcdefghijklmnopqrstuvwxyz012345")
        assert "ghp_" not in result

    def test_fake_github_fine_grained_pat_redacted(self):
        result = redact("github_pat_11ABCDEFG0123456789_abcdefghijk")
        assert "github_pat_" not in result

    def test_fake_bearer_token_redacted(self):
        result = redact("Authorization: Bearer abc123def456ghi789jkl012")
        assert "abc123def456" not in result

    def test_fake_private_key_redacted(self):
        pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEfakefakefakefake\nfakefakefake\n"
            "-----END RSA PRIVATE KEY-----"
        )
        result = redact(pem)
        assert "MIIEfake" not in result
        assert "[REDACTED:private-key]" in result

    def test_fake_password_assignment_redacted(self):
        result = redact('password = "hunter2secret"')
        assert "hunter2secret" not in result
        # The key name survives so reviewers can see what was assigned.
        assert "password" in result

    def test_plain_code_untouched(self):
        code = "def add(a, b):\n    return a + b\n"
        assert redact(code) == code

    def test_contains_secret_detects_leftovers(self):
        assert contains_secret("Bearer abcdefghijklmnop123456")
        assert not contains_secret("nothing to see here")
