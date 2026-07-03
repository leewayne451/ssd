"""Deny-first path filtering: security files in, sensitive paths always out."""

import pytest

from tools.ai_review.path_filter import decide, filter_paths, is_denied


class TestIncludedPaths:
    def test_security_file_included(self):
        decision = decide("app/security/rbac.py")
        assert decision.included

    def test_route_file_included(self):
        assert decide("app/web/routes/auth_routes.py").included

    def test_service_file_included(self):
        assert decide("app/services/order_service.py").included

    def test_model_file_included(self):
        assert decide("app/models/user.py").included

    def test_test_file_included(self):
        assert decide("tests/security/test_csrf.py").included

    def test_workflow_file_included(self):
        assert decide(".github/workflows/ci.yml").included

    def test_security_file_outranks_template(self):
        included, _ = filter_paths(
            ["app/web/templates/base.html", "app/security/rbac.py"]
        )
        assert [d.path for d in included][0] == "app/security/rbac.py"


class TestSkippedPaths:
    def test_css_only_change_skipped(self):
        decision = decide("app/web/static/css/main.css")
        assert not decision.included
        assert decision.reason == "not_relevant"

    def test_image_only_change_skipped(self):
        assert not decide("app/web/static/img/logo.png").included


class TestDeniedPaths:
    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            ".env.production",
            "instance/chateau.db",
            "instance/anything.txt",
            "chateau.sqlite3",
            "uploads/user1/passport.jpg",
            "backups/2026-07-01.tar.gz",
            "logs/security.log",
            "app/audit.log",
            "deploy/aws/server.pem",
            "deploy/aws/student31.ppk",
            "secrets/private.key",
            ".ssh/id_rsa",
            ".aws/credentials",
            ".venv/lib/site-packages/flask/app.py",
            "node_modules/lodash/index.js",
            "app/__pycache__/config.cpython-312.pyc",
            ".coverage",
        ],
    )
    def test_sensitive_path_denied(self, path):
        assert is_denied(path)
        decision = decide(path)
        assert not decision.included
        assert decision.reason == "sensitive_or_generated"

    def test_deny_wins_over_relevant_directory(self):
        # Even inside a high-priority directory, secret-shaped files stay out.
        assert not decide("app/security/signing.key").included

    def test_windows_separators_normalised(self):
        assert is_denied("instance\\chateau.db")
