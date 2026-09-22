"""Document indexing, retrieval, and grounded answer generation for SourceLens."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sklearn.feature_extraction.text import TfidfVectorizer

from loaders import NotebookFileLoader


@dataclass(frozen=True)
class RetrievedChunk:
    """A retrieved document chunk paired with its similarity score."""

    document: Document
    score: float


@dataclass(frozen=True)
class Answer:
    """A grounded answer and the source chunks used to produce it."""

    text: str
    sources: tuple[RetrievedChunk, ...]
    mode: str


class TfidfRetriever:
    """Small local retriever suitable for a transparent classroom RAG demo."""

    def __init__(self, documents: list[Document]) -> None:
        """Fit a TF-IDF index over document chunks."""
        if not documents:
            raise ValueError("At least one document is required")
        self.documents = documents
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.matrix = self.vectorizer.fit_transform(doc.page_content for doc in documents)

    def retrieve(self, query: str, *, top_k: int = 4) -> list[RetrievedChunk]:
        """Return the most similar chunks in descending score order."""
        if not query.strip():
            raise ValueError("Question cannot be empty")
        query_vector = self.vectorizer.transform([query])
        scores = (self.matrix @ query_vector.T).toarray().ravel()
        indexes = np.argsort(scores)[::-1][:top_k]
        return [
            RetrievedChunk(document=self.documents[index], score=float(scores[index]))
            for index in indexes
        ]


class RAGService:
    """Maintain a notebook index and answer only from retrieved evidence."""

    MIN_RELEVANCE = 0.045

    def __init__(self) -> None:
        """Create an empty notebook and configure deterministic chunking."""
        self._documents: list[Document] = []
        self._retriever: TfidfRetriever | None = None
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=900,
            chunk_overlap=120,
            add_start_index=True,
        )
        self._chain = self._build_gemini_chain()

    @property
    def source_names(self) -> list[str]:
        """Return sorted unique filenames currently in the notebook."""
        return sorted({str(doc.metadata["source"]) for doc in self._documents})

    @property
    def chunk_count(self) -> int:
        """Return the number of searchable chunks in the notebook."""
        return len(self._documents)

    @property
    def answer_mode(self) -> str:
        """Describe whether answers use Gemini or local extractive fallback."""
        return "Gemini generation" if self._chain is not None else "local extractive fallback"

    def add_file(self, file_path: str | Path) -> int:
        """Load, split, and index a file; return the number of chunks added."""
        loaded = NotebookFileLoader(file_path).load()
        chunks = self._splitter.split_documents(loaded)
        if not chunks:
            raise ValueError(f"No searchable content found in {Path(file_path).name}")
        self._documents.extend(chunks)
        self._retriever = TfidfRetriever(self._documents)
        return len(chunks)

    def reset(self) -> None:
        """Remove every source and discard the current search index."""
        self._documents.clear()
        self._retriever = None

    def answer(self, question: str) -> Answer:
        """Retrieve relevant chunks and return a cited, grounded answer."""
        if self._retriever is None:
            raise RuntimeError("Add at least one source before asking a question")
        matches = self._retriever.retrieve(question)
        relevant = tuple(match for match in matches if match.score > 0)
        if not relevant or relevant[0].score < self.MIN_RELEVANCE:
            return Answer(
                text=(
                    "I don't know based on the uploaded sources. Try rephrasing the "
                    "question or add a document that covers the topic."
                ),
                sources=tuple(matches[:2]),
                mode=self.answer_mode,
            )

        selected = relevant[:4]
        if self._chain is not None:
            context = self._format_context(selected)
            text = self._chain.invoke({"question": question, "context": context})
        else:
            text = self._extractive_answer(question, selected)
        return Answer(text=text, sources=selected, mode=self.answer_mode)

    @staticmethod
    def _format_context(matches: tuple[RetrievedChunk, ...]) -> str:
        """Format numbered evidence blocks for the generation prompt."""
        blocks = []
        for number, match in enumerate(matches, start=1):
            metadata = match.document.metadata
            location = metadata.get("page") or metadata.get("row") or metadata.get("start_index")
            label = f"{metadata['source']}"
            if location is not None:
                label += f" (location {location})"
            blocks.append(f"[{number}] Source: {label}\n{match.document.page_content}")
        return "\n\n".join(blocks)

    @staticmethod
    def _extractive_answer(
        question: str, matches: tuple[RetrievedChunk, ...]
    ) -> str:
        """Build a concise cited answer without sending data to an external LLM."""
        query_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
        candidates: list[tuple[float, int, str]] = []
        for source_number, match in enumerate(matches, start=1):
            sentences = re.split(r"(?<=[.!?])\s+|\n+", match.document.page_content)
            for sentence in sentences:
                clean = sentence.strip()
                if len(clean) < 20:
                    continue
                terms = set(re.findall(r"[a-z0-9]+", clean.lower()))
                overlap = len(query_terms & terms)
                score = match.score + (overlap / max(len(query_terms), 1))
                candidates.append((score, source_number, clean))

        chosen: list[str] = []
        seen: set[str] = set()
        for _, source_number, sentence in sorted(candidates, reverse=True):
            fingerprint = sentence.lower()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            chosen.append(f"{sentence} [{source_number}]")
            if len(chosen) == 3:
                break
        return " ".join(chosen) if chosen else "I don't know based on the uploaded sources."

    @staticmethod
    def _build_gemini_chain():
        """Create an optional Gemini chain only when credentials are configured."""
        if not os.getenv("GOOGLE_API_KEY"):
            return None
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise RuntimeError("Install the 'gemini' extra to use GOOGLE_API_KEY") from exc

        model = ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
            temperature=0,
        )
        prompt = ChatPromptTemplate.from_template(
            """You are a careful research assistant. Answer only from the numbered
context below. Cite factual claims with matching bracketed source numbers such
as [1]. If the context does not answer the question, say that you do not know.
Use at most four concise sentences.

Question: {question}

Context:
{context}

Answer:"""
        )
        return prompt | model | StrOutputParser()

