"""Tests for SourceLens indexing, retrieval, and grounded fallback behavior."""

import sys
import types

import pytest
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from rag_service import RAGService, RetrievedChunk, TfidfRetriever


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
    assert answer.sources == ()


def test_empty_notebook_rejects_questions(monkeypatch) -> None:
    """Questions should fail clearly until at least one source is indexed."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    service = RAGService()

    with pytest.raises(RuntimeError, match="Add at least one source"):
        service.answer("What does the policy say?")


def test_retriever_handles_short_and_stopword_only_documents() -> None:
    """Valid small documents should not trigger TF-IDF's empty-vocabulary error."""
    retriever = TfidfRetriever(
        [Document(page_content="R"), Document(page_content="to be or not to be")]
    )

    assert retriever.retrieve("R", top_k=1)[0].document.page_content == "R"
    assert retriever.retrieve("to be", top_k=1)[0].score > 0


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_retriever_rejects_invalid_top_k(top_k) -> None:
    """Invalid result limits must not produce surprising Python slices."""
    retriever = TfidfRetriever([Document(page_content="alpha")])

    with pytest.raises(ValueError, match="positive integer"):
        retriever.retrieve("alpha", top_k=top_k)


def test_retriever_uses_stable_order_for_tied_scores() -> None:
    """Equal scores should preserve upload order for deterministic citations."""
    first = Document(page_content="shared term", metadata={"source": "first.txt"})
    second = Document(page_content="shared term", metadata={"source": "second.txt"})

    matches = TfidfRetriever([first, second]).retrieve("shared")

    assert [match.document for match in matches] == [first, second]


def test_retriever_does_not_rank_on_incidental_stop_words() -> None:
    """Content terms, not a shared word such as 'is', should drive retrieval."""
    retriever = TfidfRetriever(
        [Document(page_content="MFA is required."), Document(page_content="Lunch is served.")]
    )

    matches = retriever.retrieve("What is lunch?", top_k=2)

    assert matches[0].document.page_content == "Lunch is served."
    assert matches[1].score == 0


def test_retriever_copies_input_document_list() -> None:
    """External list mutation must not desynchronize documents from its matrix."""
    documents = [Document(page_content="alpha")]
    retriever = TfidfRetriever(documents)
    documents.append(Document(page_content="beta"))

    assert len(retriever.retrieve("alpha")) == 1


def test_failed_index_update_leaves_existing_notebook_usable(tmp_path, monkeypatch) -> None:
    """A failed fit must not partially append chunks to service state."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    valid = tmp_path / "valid.txt"
    invalid = tmp_path / "invalid.txt"
    valid.write_text("MFA is required.", encoding="utf-8")
    invalid.write_text("!!!", encoding="utf-8")
    service = RAGService()
    service.add_file(valid)

    with pytest.raises(ValueError, match="searchable letters or numbers"):
        service.add_file(invalid)

    assert service.source_names == ["valid.txt"]
    assert "MFA is required" in service.answer("Is MFA required?").text


def test_chunking_drops_unsearchable_fragments_without_rejecting_file(
    tmp_path, monkeypatch
) -> None:
    """A decorative chunk should not poison useful chunks from the same source."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    path = tmp_path / "decorated.txt"
    path.write_text("policy " * 150 + "\n\n" + "!" * 1_000, encoding="utf-8")
    service = RAGService()

    added = service.add_file(path)

    assert added >= 1
    assert all(any(character.isalnum() for character in doc.page_content) for doc in service._documents)


def test_offline_answer_keeps_short_evidence_and_excludes_unrelated_sentences(
    tmp_path, monkeypatch
) -> None:
    """Short direct answers are useful, while zero-overlap filler is not."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    path = tmp_path / "policy.txt"
    path.write_text("MFA is required. Lunch is at noon.", encoding="utf-8")
    service = RAGService()
    service.add_file(path)

    answer = service.answer("Is MFA required?")

    assert answer.text == "MFA is required. [1]"


def test_offline_answer_matches_unicode_terms(tmp_path, monkeypatch) -> None:
    """Non-ASCII source text should work in the local extraction path."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    path = tmp_path / "policy.txt"
    path.write_text("Le résumé est obligatoire.", encoding="utf-8")
    service = RAGService()
    service.add_file(path)

    answer = service.answer("Le résumé est-il obligatoire?")

    assert answer.text == "Le résumé est obligatoire. [1]"


def test_context_citation_preserves_zero_character_location() -> None:
    """The first chunk's start index is a real location, not a missing value."""
    match = RetrievedChunk(
        Document(page_content="evidence", metadata={"source": "a.txt", "start_index": 0}),
        score=1.0,
    )

    context = RAGService._format_context((match,))

    assert "a.txt (character 0)" in context


@pytest.mark.parametrize("hosted_result", [ConnectionError("offline"), "   "])
def test_gemini_failure_falls_back_to_local_answer(
    tmp_path, monkeypatch, hosted_result
) -> None:
    """Hosted-model failures or empty output should preserve no-key behavior."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    path = tmp_path / "policy.txt"
    path.write_text("MFA is required.", encoding="utf-8")
    service = RAGService()
    service.add_file(path)

    class FailingChain:
        def invoke(self, inputs):
            if isinstance(hosted_result, Exception):
                raise hosted_result
            return hosted_result

    service._chain = FailingChain()
    answer = service.answer("Is MFA required?")

    assert answer.text == "MFA is required. [1]"
    assert answer.mode == "local extractive fallback (Gemini unavailable)"


def test_successful_gemini_chain_remains_the_preferred_mode(tmp_path, monkeypatch) -> None:
    """A working optional chain should still supply the final cited answer."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    path = tmp_path / "policy.txt"
    path.write_text("MFA is required.", encoding="utf-8")
    service = RAGService()
    service.add_file(path)
    service._chain = RunnableLambda(lambda inputs: "Hosted answer. [1]")

    answer = service.answer("Is MFA required?")

    assert answer.text == "Hosted answer. [1]"
    assert answer.mode == "Gemini generation"


def test_whitespace_api_key_keeps_service_offline(monkeypatch) -> None:
    """Whitespace is not a configured credential and must not import Gemini."""
    monkeypatch.setenv("GOOGLE_API_KEY", "   ")

    assert RAGService().answer_mode == "local extractive fallback"


def test_blank_model_setting_uses_default_without_hardcoded_key(monkeypatch) -> None:
    """Gemini configuration should read credentials and model choice from the environment."""
    captured = {}
    fake_module = types.ModuleType("langchain_google_genai")

    def fake_model(**kwargs):
        captured.update(kwargs)
        return RunnableLambda(lambda prompt: "Hosted answer. [1]")

    fake_module.ChatGoogleGenerativeAI = fake_model
    monkeypatch.setitem(sys.modules, "langchain_google_genai", fake_module)
    monkeypatch.setenv("GOOGLE_API_KEY", "environment-secret")
    monkeypatch.setenv("GOOGLE_MODEL", "   ")

    chain = RAGService._build_gemini_chain()

    assert chain is not None
    assert captured == {"model": "gemini-2.5-flash", "temperature": 0}
