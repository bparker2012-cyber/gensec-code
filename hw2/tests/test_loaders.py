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


def test_loader_rechecks_size_before_lazy_read(tmp_path) -> None:
    """A file that grows after loader construction must not bypass the limit."""
    path = tmp_path / "notes.txt"
    path.write_text("small", encoding="utf-8")
    loader = NotebookFileLoader(path, max_bytes=5)
    path.write_text("now too large", encoding="utf-8")

    with pytest.raises(ValueError, match="5-byte limit"):
        loader.load()


def test_loader_rejects_non_positive_size_limit(tmp_path) -> None:
    """A nonsensical upload limit should fail at configuration time."""
    path = tmp_path / "notes.txt"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="greater than zero"):
        NotebookFileLoader(path, max_bytes=0)


def test_csv_skips_empty_rows_and_keeps_physical_row_number(tmp_path) -> None:
    """Delimiter-only rows should not become fake labeled documents."""
    path = tmp_path / "controls.csv"
    path.write_text("id,owner\n,\nIR-04,SOC\n", encoding="utf-8")

    documents = NotebookFileLoader(path).load()

    assert len(documents) == 1
    assert documents[0].metadata["row"] == 3
    assert "IR-04" in documents[0].page_content


@pytest.mark.parametrize("header", ["id,id", "id,"])
def test_csv_rejects_headers_that_would_lose_data(tmp_path, header) -> None:
    """Duplicate or blank field names must not be silently normalized."""
    path = tmp_path / "controls.csv"
    path.write_text(f"{header}\nAC-01,IAM\n", encoding="utf-8")

    with pytest.raises(ValueError, match="non-empty and unique"):
        NotebookFileLoader(path).load()


def test_csv_rejects_rows_wider_than_header(tmp_path) -> None:
    """Extra fields should report malformed input instead of using a None label."""
    path = tmp_path / "controls.csv"
    path.write_text("id,owner\nAC-01,IAM,unexpected\n", encoding="utf-8")

    with pytest.raises(ValueError, match="row 2 has more values"):
        NotebookFileLoader(path).load()
