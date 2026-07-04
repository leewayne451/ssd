"""Manifest-driven trusted document loading."""

import pytest

from tools.ai_review.document_loader import (
    STATUS_EXTRACTION_FAILED,
    STATUS_LOADED,
    STATUS_MISSING,
    load_documents,
    load_manifest,
)

MANIFEST = """
documents:
  - glob: docs/requirements.md
    category: requirements
    authority: primary
    priority: 90
    relevant_code_paths: ["app/**"]
    maximum_characters: 500
    enabled_for_pr_review: true
    enabled_for_milestone_audit: true
  - glob: docs/usecases.md
    category: use-misuse-cases
    priority: 80
    relevant_code_paths: ["app/security/**"]
    ignore_diagrams: true
  - glob: docs/settings.yml
    category: workflow-states
    priority: 70
    relevant_code_paths: ["app/**"]
  - glob: docs/data.json
    category: database-design
    priority: 60
    relevant_code_paths: ["app/models/**"]
  - glob: docs/missing.md
    category: threat-model
    priority: 50
    relevant_code_paths: ["app/**"]
  - glob: docs/report.pdf
    category: deliverable-1-brief
    priority: 40
    relevant_code_paths: ["app/**"]
  - glob: docs/audit_only.md
    category: development-plan
    priority: 30
    relevant_code_paths: ["app/**"]
    enabled_for_pr_review: false
"""


@pytest.fixture()
def doc_repo(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirements.md").write_text("# FR-1\nServer-side validation. " * 40)
    (docs / "usecases.md").write_text("MUC-3: attacker replays session token.")
    (docs / "settings.yml").write_text("states: [Available, Committed, Sold]\n")
    (docs / "data.json").write_text('{"tables": ["user", "order"]}')
    (docs / "report.pdf").write_bytes(b"%PDF-1.4 not really a valid pdf")
    (docs / "audit_only.md").write_text("Milestone plan text.")
    manifest = tmp_path / "manifest.yml"
    manifest.write_text(MANIFEST)
    return tmp_path, manifest


class TestManifest:
    def test_manifest_parses_fields(self, doc_repo):
        _, manifest = doc_repo
        entries = load_manifest(manifest)
        assert entries[0].category == "requirements"
        assert entries[0].maximum_characters == 500
        assert entries[1].ignore_diagrams is True
        assert entries[6].enabled_for_pr_review is False


class TestLoading:
    def test_markdown_yaml_json_loaded(self, doc_repo, settings):
        root, manifest = doc_repo
        ctx = load_documents(
            manifest, root, settings, purpose="pr_review",
            changed_paths=["app/models/user.py", "app/security/rbac.py"],
        )
        loaded = {d.category: d for d in ctx.documents}
        assert loaded["requirements"].status == STATUS_LOADED
        assert "Available" in loaded["workflow-states"].text
        assert '"user"' in loaded["database-design"].text

    def test_markdown_truncated_to_entry_limit(self, doc_repo, settings):
        root, manifest = doc_repo
        ctx = load_documents(
            manifest, root, settings, purpose="pr_review",
            changed_paths=["app/models/user.py"],
        )
        req = next(d for d in ctx.documents if d.category == "requirements")
        assert req.truncated
        assert len(req.text) <= 500 + 100

    def test_ignore_diagrams_note_added(self, doc_repo, settings):
        root, manifest = doc_repo
        ctx = load_documents(
            manifest, root, settings, purpose="pr_review",
            changed_paths=["app/security/rbac.py"],
        )
        usecases = next(d for d in ctx.documents if d.category == "use-misuse-cases")
        assert "Diagrams" in usecases.note
        assert "ignored" in usecases.note

    def test_missing_document_reported(self, doc_repo, settings):
        root, manifest = doc_repo
        ctx = load_documents(
            manifest, root, settings, purpose="milestone_audit"
        )
        missing = [d for d in ctx.unavailable if d.status == STATUS_MISSING]
        assert any(d.category == "threat-model" for d in missing)
        assert "INSUFFICIENT_EVIDENCE" in ctx.as_text()

    def test_failed_pdf_extraction_reported(self, doc_repo, settings):
        root, manifest = doc_repo
        ctx = load_documents(
            manifest, root, settings, purpose="milestone_audit"
        )
        failed = [d for d in ctx.unavailable if d.status == STATUS_EXTRACTION_FAILED]
        assert any(d.category == "deliverable-1-brief" for d in failed)


def _write_minimal_pdf(path, text: str) -> None:
    """Build a tiny valid one-page PDF containing the given text."""
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    path.write_bytes(bytes(out))


class TestPdfExtraction:
    def test_bounded_pdf_extraction(self, doc_repo, settings):
        root, manifest = doc_repo
        _write_minimal_pdf(root / "docs" / "report.pdf", "SFR-2 admin MFA required")
        ctx = load_documents(manifest, root, settings, purpose="milestone_audit")
        pdf_doc = next(
            d for d in ctx.documents if d.category == "deliverable-1-brief"
        )
        assert pdf_doc.status == STATUS_LOADED
        assert "SFR-2" in pdf_doc.text
        assert len(pdf_doc.text) <= settings.max_doc_chars + 100

    def test_malformed_pdf_fails_safely(self, doc_repo, settings):
        root, manifest = doc_repo
        (root / "docs" / "report.pdf").write_bytes(b"%PDF-1.4 broken content without xref")

        ctx = load_documents(manifest, root, settings, purpose="milestone_audit")
        pdf_doc = next(
            d for d in ctx.unavailable if d.category == "deliverable-1-brief"
        )
        assert pdf_doc.status == STATUS_EXTRACTION_FAILED
        assert "no extractable text" in pdf_doc.note or "extraction failed" in pdf_doc.note


class TestRelevance:
    def test_pr_review_selects_only_relevant_documents(self, doc_repo, settings):
        root, manifest = doc_repo
        ctx = load_documents(
            manifest, root, settings, purpose="pr_review",
            changed_paths=["app/models/user.py"],
        )
        categories = {d.category for d in ctx.documents}
        assert "database-design" in categories
        # Only relevant to app/security/** changes:
        assert "use-misuse-cases" not in categories
        # Disabled for PR review:
        assert "development-plan" not in categories

    def test_milestone_audit_uses_broader_set(self, doc_repo, settings):
        root, manifest = doc_repo
        ctx = load_documents(manifest, root, settings, purpose="milestone_audit")
        categories = {d.category for d in ctx.documents}
        assert "development-plan" in categories
        assert "use-misuse-cases" in categories
