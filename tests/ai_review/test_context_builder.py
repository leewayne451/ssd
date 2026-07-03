"""Bounded diff-context construction."""

from tools.ai_review.context_builder import FileDiff, build_diff_context


def _diff(path: str, size: int = 100) -> FileDiff:
    return FileDiff(path=path, patch=("+x = 1\n" * (size // 7 + 1))[:size])


class TestContextBuilder:
    def test_filenames_preserved(self, settings):
        ctx = build_diff_context([_diff("app/security/rbac.py")], settings)
        assert "--- FILE: app/security/rbac.py" in ctx.text
        assert ctx.included_files == ["app/security/rbac.py"]

    def test_per_file_limit_enforced(self, settings):
        ctx = build_diff_context(
            [_diff("app/services/order_service.py", size=5_000)], settings
        )
        assert "TRUNCATED" in ctx.text
        assert ctx.truncated
        assert "app/services/order_service.py" in ctx.truncated_files

    def test_total_limit_enforced(self, settings):
        diffs = [
            _diff(f"app/services/service_{i}.py", size=490) for i in range(20)
        ]
        ctx = build_diff_context(diffs, settings)
        assert ctx.truncated
        assert ctx.omitted_files  # some files did not fit at all
        assert len(ctx.text) <= settings.max_context_chars + 500

    def test_priority_ordering(self, settings):
        ctx = build_diff_context(
            [
                _diff("tests/unit/test_auth.py"),
                _diff("app/security/password_policy.py"),
                _diff("app/web/routes/cart_routes.py"),
            ],
            settings,
        )
        assert ctx.included_files == [
            "app/security/password_policy.py",
            "app/web/routes/cart_routes.py",
            "tests/unit/test_auth.py",
        ]

    def test_not_truncated_when_within_limits(self, settings):
        ctx = build_diff_context([_diff("app/models/user.py", size=50)], settings)
        assert not ctx.truncated
        assert not ctx.truncated_files

    def test_sensitive_files_never_enter_context(self, settings):
        ctx = build_diff_context(
            [_diff(".env"), _diff("instance/chateau.db"), _diff("app/models/user.py")],
            settings,
        )
        assert ".env" not in ctx.text
        assert "chateau.db" not in ctx.text
        assert [d.path for d in ctx.excluded] != []

    def test_diff_content_redacted(self, settings):
        secret = "ghp_abcdefghijklmnopqrstuvwxyz012345"
        ctx = build_diff_context(
            [FileDiff("app/config.py", f"+TOKEN = '{secret}'")], settings
        )
        assert secret not in ctx.text

    def test_no_content_flag(self, settings):
        ctx = build_diff_context([_diff("app/web/static/css/main.css")], settings)
        assert not ctx.has_content
