# SourceLens Screencast Script

Target length: 4 minutes 30 seconds. Keep the webcam visible for the opening,
then share the terminal, application, and GitHub browser in the order below.
Words in brackets are actions, not narration.

## 0:00 to 0:20 — Camera introduction

[Start recording with the webcam on. Do not share the screen yet.]

"Hi, I’m Brehon Parker, and this is my Homework 2 application, SourceLens.
SourceLens is a small NotebookLM-style LangChain RAG app. It builds a notebook
from files I provide, retrieves the most relevant passages, answers only from
that evidence, and exposes its sources and relevance scores so the response is
easy to verify. I’ll begin from a fresh Git clone, demonstrate both a successful
answer and a limitation, and then walk through every commit on GitHub."

## 0:20 to 0:50 — Clone and setup in a fresh directory

[Share the terminal. Use a new folder outside the development project. Paste
the repository URL into the marked command before recording.]

```bash
mkdir -p ~/hw2-screencast-demo
cd ~/hw2-screencast-demo
git clone REPOSITORY_URL
cd REPOSITORY_NAME/hw2
uv sync --extra dev
uv run pytest -q
uv run chainlit run app.py
```

"I’m cloning my course repository into a new directory that is not under my
development project, exactly as the assignment requires. Inside `hw2`, `uv
sync` creates the isolated environment from the committed project and lock
files. The test suite passes before I run the app. No secret appears in source
control: Gemini is optional, and its API key is read only from the
`GOOGLE_API_KEY` environment variable. For this demo I’m using the built-in
local mode, so no uploaded document content leaves the computer."

## 0:50 to 2:05 — Application capabilities

[Open the Chainlit URL. Upload `incident_response.md` and
`security_controls.csv` from `hw2/sample_data`.]

"The welcome screen lists six supported formats: text, Markdown, CSV, JSON,
PDF, and DOCX. I’m uploading a Markdown handbook and a CSV control catalog.
The custom loader normalizes both formats into LangChain Documents, and the app
reports the number of indexed sources and chunks."

[Ask: `When must the privacy officer be notified for a Severity 1 incident?`]

"This is a grounded question. SourceLens retrieves the relevant chunk and
answers that the privacy officer must be notified within 30 minutes. The answer
includes citation number one, the source filename, its location, and the
numeric relevance score. Those details make the retrieval step visible instead
of presenting an unsupported chatbot answer."

[Enter `/sources`.]

"The `/sources` command confirms which files are in this session and how many
chunks are searchable. I can use `/add` for more files or `/reset` to clear the
notebook. Each browser chat has its own in-memory service, so one user’s files
are not mixed with another session."

## 2:05 to 2:35 — Honest limitation demo

[Ask: `What is the cafeteria menu on Friday?`]

"This question is outside the uploaded evidence. The relevance gate prevents a
confident-looking guess, and SourceLens says it does not know based on the
sources. That is an intentional limitation. The local TF-IDF retriever is
private and transparent, but it depends on overlapping vocabulary and may miss
synonyms. It also cannot OCR scanned PDFs or reason over images. Gemini mode can
write smoother summaries, but it still uses the same retrieved evidence and is
subject to API access and quota."

## 2:35 to 4:20 — GitHub commit-diff walkthrough

[Open the GitHub repository. Open each commit and show its Files changed diff.]

"Now I’ll explain the implementation through the repository history rather
than through my working copy. The first commit, `Initialize Homework 2
SourceLens project`, creates the required `hw2/app.py` and
`screencast_url.txt`, plus the repository ignore rules. The ignore file excludes
the virtual environment, API environment files, caches, and compiled Python so
credentials and generated files do not enter Git."

[Open the custom-loader commit.]

"The second commit, `Add custom multi-format LangChain loader`, is the first
major feature. In `loaders.py`, `NotebookFileLoader` extends LangChain’s
`BaseLoader`. It validates the path, suffix, and ten-megabyte limit, then lazily
loads text, Markdown, JSON, PDF, DOCX, or CSV. PDF pages and CSV rows become
separate Documents, while every format receives consistent source metadata.
The accompanying tests verify metadata, CSV row locations, JSON handling,
unsupported formats, and edge cases. `pyproject.toml` declares the project and
optional Gemini dependency; `uv.lock` is the machine-generated reproducible
dependency resolution, not application logic."

[Open the retrieval/UI commit.]

"The third commit, `Implement cited retrieval and Chainlit notebook UI`, adds
the RAG pipeline. `rag_service.py` recursively chunks documents with overlap,
builds a local TF-IDF matrix, ranks chunks, and applies a minimum relevance
threshold. `RAGService.answer` either invokes a LangChain Gemini prompt chain
or uses the local extractive fallback. Both paths return an Answer object with
the exact retrieved chunks. In `app.py`, Chainlit stores one RAGService per
session, manages uploads and commands, runs blocking retrieval off the event
loop, and formats numbered evidence with locations and scores. The tests cover
successful grounding, citations, unknown questions, and an empty notebook."

[Open the final agent-review commit once its final title is known.]

"The final commit records the focused coding-agent review. I used the agent to
challenge loader and retrieval edge cases, added regression tests for the
identified failures, and reran the complete suite. The README documents setup,
architecture, the demo path, and the same limitations I showed here."

## 4:20 to 4:30 — Close

[Return briefly to the running app or repository root.]

"That completes SourceLens: a tested, source-citing LangChain RAG notebook with
a custom loader, reproducible `uv` setup, incremental Git history, and visible
failure behavior. Thank you."
