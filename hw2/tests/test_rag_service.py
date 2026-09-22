"""Tests for SourceLens indexing, retrieval, and grounded fallback behavior."""

import pytest

from rag_service import RAGService


def test_service_retrieves_and_cites_uploaded_evidence(tmp_path, monkeypatch) -> None:
    """A supported question should return source-grounded text and citations."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    path = tmp_path / "handbook.md"
    path.write_text(
        "Severity 1 incidents require notifying the privacy officer within 30 minutes.",
        encoding="utf-8",
    )
    service = RAGService()
    service.add_file(path)

    answer = service.answer("When is the privacy officer notified?")

    assert "30 minutes" in answer.text
    assert "[1]" in answer.text
    assert answer.sources[0].document.metadata["source"] == "handbook.md"
    assert answer.mode == "local extractive fallback"


def test_service_admits_when_sources_do_not_cover_question(tmp_path, monkeypatch) -> None:
    """An unrelated question should exercise the application's limitation path."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    path = tmp_path / "handbook.txt"
    path.write_text("Firewall logs are retained for 365 days.", encoding="utf-8")
    service = RAGService()
    service.add_file(path)

    answer = service.answer("What is the cafeteria menu on Friday?")

    assert answer.text.startswith("I don't know")


def test_empty_notebook_rejects_questions(monkeypatch) -> None:
    """Questions should fail clearly until at least one source is indexed."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    service = RAGService()

    with pytest.raises(RuntimeError, match="Add at least one source"):
        service.answer("What does the policy say?")

