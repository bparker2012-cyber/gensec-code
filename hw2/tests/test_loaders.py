"""Tests for the custom multi-format loader."""

import json

import pytest

from loaders import NotebookFileLoader


def test_text_file_receives_consistent_source_metadata(tmp_path) -> None:
    """Text input should become a LangChain document with source metadata."""
    path = tmp_path / "notes.txt"
    path.write_text("Rotate service credentials every 90 days.", encoding="utf-8")

    documents = NotebookFileLoader(path).load()

    assert documents[0].page_content.startswith("Rotate service")
    assert documents[0].metadata == {"source": "notes.txt", "file_type": ".txt"}


def test_csv_yields_one_document_per_data_row(tmp_path) -> None:
    """CSV rows should remain independently retrievable and keep row numbers."""
    path = tmp_path / "controls.csv"
    path.write_text("id,owner\nAC-01,IAM\nIR-04,SOC\n", encoding="utf-8")

    documents = NotebookFileLoader(path).load()

    assert len(documents) == 2
    assert documents[1].metadata["row"] == 3
    assert "owner: SOC" in documents[1].page_content


def test_json_is_validated_and_pretty_printed(tmp_path) -> None:
    """Valid JSON should be normalized into readable text."""
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"retention_days": 365}), encoding="utf-8")

    document = NotebookFileLoader(path).load()[0]

    assert '"retention_days": 365' in document.page_content


def test_unsupported_extension_is_rejected(tmp_path) -> None:
    """Unexpected formats should fail with a clear validation message."""
    path = tmp_path / "archive.zip"
    path.write_bytes(b"not a document")

    with pytest.raises(ValueError, match="Unsupported file type"):
        NotebookFileLoader(path)

