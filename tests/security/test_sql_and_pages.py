"""M6 — SQLi-prevention guard + no-unsafe-rendering (T-40) — static checks.

Route/template render tests (T-39, T-41) live in
tests/integration/test_error_pages.py, because this security suite's
conftest swaps in a minimal app without the real templates.
"""

import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"

# Raw-SQL smells: a literal SELECT/INSERT/... string, or db.session.execute on a
# bare string. We use the ORM everywhere (SDR-03), so these must not appear in
# app/ business code.
_RAW_SQL_RE = re.compile(
    r"""(execute\(\s*["'](?:\s*)(?:select|insert|update|delete|drop)\b)"""
    r"""|(["'](?:select|insert|update|delete)\b[^"']*\b(?:from|into|set)\b)""",
    re.IGNORECASE,
)


def test_no_raw_sql_strings_in_app_code():
    """T-40 (OWASP row 6): no hand-built SQL anywhere under app/."""
    offenders = []
    for path in APP_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _RAW_SQL_RE.search(line):
                offenders.append(f"{path.relative_to(APP_DIR.parent)}:{lineno}: {line.strip()}")
    assert not offenders, "raw SQL found:\n" + "\n".join(offenders)


def test_no_jinja_safe_filter_on_user_data():
    """|safe / autoescape-off must never wrap user data in templates (SDR-02)."""
    templates = (APP_DIR / "web" / "templates").rglob("*.html")
    offenders = []
    for path in templates:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "|safe" in text or "autoescape false" in text:
            offenders.append(str(path))
    assert not offenders, "unsafe rendering found in: " + ", ".join(offenders)
