# SourceLens

SourceLens is a NotebookLM-style LangChain retrieval-augmented generation
application created for Homework 2. It indexes a small set of uploaded files,
retrieves relevant chunks, answers from that evidence, and shows exactly which
sources supported the response.

The implementation starts from the course repository's
`02_LangChain/07_RAG` examples. It retains their `Document` model, recursive
text splitting, retrieval-then-answer flow, environment-based model settings,
and Chainlit event handlers, then adds a custom loader, an offline retriever,
multi-file notebooks, citations, scores, and explicit limitation behavior.

## Features

- Custom `NotebookFileLoader(BaseLoader)` for TXT, Markdown, CSV, JSON, PDF,
  and DOCX files.
- Per-chat notebooks with recursive chunking and local TF-IDF retrieval.
- Numbered evidence citations, source locations, and visible relevance scores.
- `/add`, `/sources`, `/reset`, and `/help` commands.
- A useful local extractive mode with no API key or data transmission.
- Optional Gemini generation when `GOOGLE_API_KEY` is present.
- Validation for unsupported, oversized, empty, and image-only input.

## Run with uv

From a fresh clone of the course repository:

```bash
cd hw2
uv sync --extra dev
uv run chainlit run app.py -w
```

Open the local URL shown in the terminal. Upload both files in `sample_data/`
for a predictable demo.

To enable Gemini generation, install the optional dependency and export the
key without putting it in source code:

```bash
uv sync --extra dev --extra gemini
export GOOGLE_API_KEY="your-key"
export GOOGLE_MODEL="gemini-2.5-flash"
uv run chainlit run app.py -w
```

The committed `.env.example` documents these variables, while `.env` and
`.venv` are ignored by Git.

## Test

```bash
cd hw2
uv run pytest -q
```

The tests cover loader metadata, CSV rows, JSON validation, rejected formats,
grounded retrieval, citations, unknown questions, and empty-notebook errors.

## Five-minute demo path

1. Upload `sample_data/incident_response.md` and
   `sample_data/security_controls.csv`.
2. Ask: `When must the privacy officer be notified for a Severity 1 incident?`
3. Run `/sources` to show the indexed notebook.
4. Ask: `What is the cafeteria menu on Friday?` to demonstrate that the app
   refuses unsupported claims.
5. Explain that local TF-IDF is transparent and private but can miss synonyms;
   scanned PDFs also require OCR, and generated answers depend on model quota
   when Gemini mode is enabled.

## Architecture and limitations

`loaders.py` normalizes supported files into LangChain documents.
`rag_service.py` splits documents, builds the TF-IDF index, retrieves the top
chunks, applies a relevance gate, and either invokes a LangChain Gemini prompt
chain or creates a local extractive answer. `app.py` manages Chainlit sessions
and renders commands, answers, citations, and recoverable errors.

This is intentionally a small-coursework architecture. Its index is in memory,
so a restart clears uploaded content. TF-IDF relies on matching vocabulary and
does not understand images, scanned PDFs, or relationships that require broad
multi-hop reasoning. The evidence display makes those limits observable rather
than hiding them.
