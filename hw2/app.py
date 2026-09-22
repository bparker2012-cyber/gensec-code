"""Chainlit interface for the SourceLens RAG application."""

from __future__ import annotations

from pathlib import Path

import chainlit as cl

from rag_service import Answer, RAGService


ACCEPTED_TYPES = [
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]


def _service() -> RAGService:
    """Return the RAG service stored in the current user's session."""
    service = cl.user_session.get("rag_service")
    if service is None:
        service = RAGService()
        cl.user_session.set("rag_service", service)
    return service


async def _ask_for_files() -> None:
    """Prompt for notebook sources and report per-file indexing results."""
    files = await cl.AskFileMessage(
        content=(
            "Upload up to six sources (TXT, Markdown, CSV, JSON, PDF, or DOCX). "
            "Each file must be 10 MB or smaller."
        ),
        accept=ACCEPTED_TYPES,
        max_size_mb=10,
        max_files=6,
        timeout=180,
    ).send()
    if not files:
        await cl.Message(content="No files were added. Type `/add` whenever you are ready.").send()
        return

    service = _service()
    results: list[str] = []
    for uploaded in files:
        try:
            added = service.add_file(Path(uploaded.path))
            results.append(f"- Indexed **{uploaded.name}** as {added} searchable chunk(s).")
        except (OSError, ValueError) as exc:
            results.append(f"- Could not index **{uploaded.name}**: {exc}")

    results.append(
        f"\nNotebook total: **{len(service.source_names)} source(s)** and "
        f"**{service.chunk_count} chunk(s)**. Answer mode: **{service.answer_mode}**."
    )
    await cl.Message(content="\n".join(results)).send()


def _evidence_markdown(answer: Answer) -> str:
    """Render retrieved metadata as a compact evidence list."""
    lines = ["\n\n**Retrieved evidence**"]
    for number, match in enumerate(answer.sources, start=1):
        metadata = match.document.metadata
        detail = ""
        if "page" in metadata:
            detail = f", page {metadata['page']}"
        elif "row" in metadata:
            detail = f", row {metadata['row']}"
        elif "start_index" in metadata:
            detail = f", character {metadata['start_index']}"
        lines.append(
            f"- [{number}] `{metadata['source']}`{detail} "
            f"(relevance {match.score:.3f})"
        )
    lines.append(f"\n_Mode: {answer.mode}_")
    return "\n".join(lines)


@cl.on_chat_start
async def on_chat_start() -> None:
    """Create an isolated notebook and explain the available commands."""
    cl.user_session.set("rag_service", RAGService())
    await cl.Message(
        content=(
            "# SourceLens\n"
            "Ask questions grounded in your own documents. Answers include the exact "
            "sources and retrieval scores used.\n\n"
            "Commands: `/add`, `/sources`, `/reset`, and `/help`."
        )
    ).send()
    await _ask_for_files()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle notebook commands or answer a source-grounded question."""
    command = message.content.strip()
    service = _service()

    if command == "/add":
        await _ask_for_files()
        return
    if command == "/sources":
        if service.source_names:
            names = "\n".join(f"- {name}" for name in service.source_names)
            content = f"**Indexed sources**\n{names}\n\n{service.chunk_count} total chunks."
        else:
            content = "The notebook is empty. Type `/add` to upload sources."
        await cl.Message(content=content).send()
        return
    if command == "/reset":
        service.reset()
        await cl.Message(content="Notebook cleared. Type `/add` to start a new one.").send()
        return
    if command == "/help":
        await cl.Message(
            content=(
                "Upload sources with `/add`, inspect them with `/sources`, or clear them "
                "with `/reset`. Ask a specific question for the strongest retrieval. "
                "SourceLens cannot read images or scanned PDFs without OCR and may miss "
                "answers that use very different wording."
            )
        ).send()
        return

    try:
        answer = await cl.make_async(service.answer)(command)
    except (RuntimeError, ValueError) as exc:
        await cl.Message(content=f"I could not answer that yet: {exc}").send()
        return
    except Exception as exc:  # protect the chat if an optional hosted model fails
        await cl.Message(
            content=(
                "The configured generation model failed. Check the API key, quota, and "
                f"network connection, then retry. Technical detail: `{type(exc).__name__}`"
            )
        ).send()
        return

    await cl.Message(content=answer.text + _evidence_markdown(answer)).send()
