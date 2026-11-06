"""Fill the instructor's retained Word template and append verified evidence.

Run with the bundled document-authoring Python runtime (python-docx required).
Render the result with the Documents skill's render_docx.py before delivery.
"""

from datetime import datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile, ZIP_DEFLATED
from zoneinfo import ZoneInfo

from docx import Document
from docx.shared import Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evidence/sources/homework-template.docx"
OUTPUT = ROOT / "hw6-bparker2012.docx"
SOURCE_SHA = "58aca05c972a46821ba8b9d20afb3bb83abcddf90dbee4a49a1abbef6c6df72e"
REPO = "https://github.com/bparker2012-cyber/gensec-code/tree/codex/hw6-secure-notes/hw6"


def main() -> None:
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    doc = Document(SOURCE)
    original = list(doc.paragraphs)
    width = doc.sections[0].page_width - doc.sections[0].left_margin - doc.sections[0].right_margin
    transcript = json.loads((ROOT / "evidence/chat-transcript.json").read_text())
    task_items = transcript["turns"][0]["items"]
    actual_task = next(i for i in task_items if i["type"] == "userMessage")["content"][0]["text"]
    replies = [i["text"].strip() for i in task_items if i["type"] == "agentMessage"]
    prior = transcript["turns"][1]["items"]
    proposal = next(
        i["text"]
        for i in prior
        if i["type"] == "agentMessage" and "My recommendation" in i.get("text", "")
    )
    accepted = next(p for p in proposal.split("\n\n") if "My recommendation" in p).replace("**", "")
    recording = (ROOT / "screencast_url.txt").read_text().strip()
    if recording:
        parsed = urlparse(recording)
        if parsed.scheme != "https" or parsed.hostname not in {
            "youtube.com",
            "www.youtube.com",
            "youtu.be",
        }:
            raise ValueError("Use the real HTTPS YouTube watch URL.")

    def replace_text(index: int, value: str) -> None:
        # Keep paragraph/run properties intact when filling the source slots.
        nodes = original[index]._p.xpath(".//w:t")
        nodes[0].text = value
        for node in nodes[1:]:
            node.text = ""

    def replace_value(index: int, value: str) -> None:
        runs = original[index].runs
        runs[1].text = value
        for run in runs[2:]:
            run.text = ""

    replace_text(2, "Homework Assignment no. 6")
    replace_text(5, "Student name: Brehon Parker")
    replace_text(7, "FAU Email: bparker2012@fau.edu")
    replace_value(18, recording or "Pending student recording and unlisted YouTube upload")
    replace_value(20, " " + REPO)
    replace_value(22, "Secure Notes")
    replace_value(
        24,
        " Secure Notes is a local Flask application generated with OpenAI Codex. Separate "
        "user accounts can create, read, edit, and delete persistent private notes stored in SQLite.",
    )
    replace_text(27, "Development task and coding agent")
    # Empty template spacers would overflow onto a blank page.
    for index in (25, 26):
        original[index]._p.getparent().remove(original[index]._p)
    original[27].paragraph_format.page_break_before = True
    original[27].paragraph_format.keep_with_next = True
    for run in original[27].runs:
        run.italic = False
        run.bold = True
        run.font.size = Pt(14)
        run.font.name = "Liberation Sans"
    replace_text(
        28,
        "Coding agent: OpenAI Codex, Codex desktop app. I accepted the secure notes proposal "
        "and requested methodical GitHub commits. The following task text and replies come "
        "from the actual Codex conversation export. Prepared replay prompts are identified separately.",
    )
    for run in original[28].runs:
        run.italic = False

    def paragraph(text: str, bold: bool = False, size: int = 12, italic: bool = False):
        p = doc.add_paragraph(style="Body Text")
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.1
        run = p.add_run(text)
        run.bold, run.italic = bold, italic
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def heading(text: str, new_page: bool = False):
        p = paragraph(text, bold=True, size=14)
        p.runs[0].font.name = "Liberation Sans"
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.page_break_before = new_page
        return p

    def picture(filename: str, caption: str):
        p = doc.add_paragraph(style="Body Text")
        p.paragraph_format.keep_with_next = True
        shape = p.add_run().add_picture(str(ROOT / "evidence/screenshots" / filename), width=width)
        shape._inline.docPr.set("descr", caption)
        paragraph(caption, size=11, italic=True)

    paragraph("Accepted application proposal", bold=True)
    paragraph(accepted)
    paragraph("Actual task prompt", bold=True)
    paragraph(actual_task)
    paragraph("Actual Codex response", bold=True)
    paragraph(replies[0])
    picture(
        "03-vscode-actual-task-response.png",
        "Figure 1. VS Code displays exact excerpts of the real task and Codex response. "
        "The file identifies its conversation-export source and the FAU email ID is visible.",
    )

    heading("Standalone prompts for recreation", new_page=True)
    paragraph(
        "These self-contained instructions were prepared from the agreed task for the "
        "required screencast replay. They are not additional historical user messages. "
        "The complete wording and provenance are preserved in prompts.txt."
    )
    prompts = (ROOT / "prompts.txt").read_text()
    first = prompts[prompts.index("PROMPT 1") : prompts.index("PROMPT 2")].strip().splitlines()
    second = prompts[prompts.index("PROMPT 2") :].strip().splitlines()
    heading("Prompt 1 Build the application")
    paragraph(" ".join(first[1:]))
    heading("Prompt 2 Verify security and prepare the demonstration")
    paragraph(" ".join(second[1:]))

    heading("Generated application code", new_page=True)
    paragraph(
        "Codex generated app.py, local Jinja templates, CSS, and a locked dependency "
        "environment. Registration, note creation, reading, editing, deletion, and sign-out "
        "passed the initial smoke check before the application commit was pushed."
    )
    picture(
        "05-vscode-generated-app.png",
        "Figure 2. Top lines of the generated Python application in VS Code, with bparker2012 visible in the window title.",
    )
    paragraph(
        "The source remains readable and divided into a small application factory, database "
        "helpers, authentication checks, and note routes. The UI requires no JavaScript or remote services."
    )

    heading("Security verification and agent replies", new_page=True)
    paragraph(next(r for r in replies if "All 59" in r))
    picture(
        "04-vscode-verification-replies.png",
        "Figure 3. Exact Codex verification replies in a labeled VS Code transcript view.",
    )
    paragraph(
        "Testing identified an error page that tried to build URLs after a hostile Host was "
        "rejected, and oversized URL IDs that could overflow SQLite. The error handler now "
        "uses the framework response for rejected hosts, and a bounded route converter "
        "rejects invalid IDs before conversion or database access."
    )

    heading("Generated verification code", new_page=True)
    paragraph(
        "Codex added adversarial-input tests and a disposable demonstration. The --demo "
        "command calls actual Flask routes and SQLite through the test client. It uses "
        "temporary synthetic data and is separate from the live browser demonstration."
    )
    picture(
        "06-vscode-generated-demo.png",
        "Figure 4. Top lines of the generated demonstration code, with the FAU ID visible.",
    )

    heading("Private note ownership", new_page=True)
    paragraph(
        "Every note lookup includes both the note ID and the authenticated user ID. "
        "Update and delete statements repeat the owner condition. A second account "
        "cannot list, open, edit, or delete the first account's note; these requests "
        "are covered by the passing test suite."
    )
    picture(
        "08-vscode-owner-check.png",
        "Figure 5. The generated owner-scoped query and bounded note ID validation in app.py.",
    )

    heading("CSRF and authentication sessions", new_page=True)
    paragraph(
        "Every POST, including login, registration, and logout, verifies the session CSRF "
        "token. Authentication transitions clear session state and rotate the token. "
        "An opaque token in the signed cookie maps to a hashed token in SQLite, allowing "
        "logout and subsequent login to revoke captured old cookies. Sessions expire "
        "after 30 minutes."
    )
    picture(
        "09-vscode-csrf-check.png",
        "Figure 6. Request guards load the authenticated user and verify all POST form tokens.",
    )

    heading("Verification from a fresh GitHub clone", new_page=True)
    receipt = json.loads((ROOT / "evidence/runs/clean-clone-verification.json").read_text())
    paragraph(
        "A fresh clone of remote commit " + receipt["commit"][:12] + " installed the "
        "locked dependencies, passed all 59 tests, ran the security demo, and passed "
        "Ruff checks. This verifies the checked-in application from a clean checkout; "
        "it does not establish a new AI regeneration."
    )
    paragraph((ROOT / "evidence/runs/clean-clone-tests.txt").read_text().strip(), size=11)
    picture(
        "07-vscode-security-demo-results.png",
        "Figure 7. Captured output from the clean-clone in-process security demo, including expected denial responses.",
    )
    paragraph(
        "The runtime dependency audit covered seven pinned packages and reported no known "
        "vulnerabilities at check time. Tests and dependency checks cover specific cases; "
        "they are not a complete security audit."
    )

    heading("Browser demonstration", new_page=True)
    paragraph(
        "The application was also exercised in Chrome. A synthetic sample account "
        "registered successfully and created a private note. The notebook displays "
        "the saved content and presents editing and deletion controls. The complete "
        "create/read/edit/delete and sign-out flow was checked through real route handlers."
    )
    picture(
        "02-private-notebook.png",
        "Figure 8. The running local notebook with a saved synthetic note and the student identity in the footer.",
    )

    heading("Capabilities and limitations", new_page=True)
    paragraph(
        "The app supports separate accounts and persistent private notes, with password "
        "hashing, parameterized SQL, output escaping, owner checks, CSRF verification, "
        "revocable sessions, request limits, and authentication rate limits. Note content "
        "is plaintext at rest. Filesystem access exposes it, and deleted data may remain "
        "in database pages or backups. The app has no MFA, password recovery, sharing, "
        "or attachments. Public deployment requires HTTPS, a production server, "
        "operational controls, and further security review."
    )
    picture(
        "10-browser-privacy-limits.png",
        "Figure 9. The application explains its privacy limits to the user, with the FAU ID visible.",
    )

    heading("Repository history and recording", new_page=True)
    paragraph(
        "The course repository records development in successive stages, rather than "
        "one final code dump: b9b0d7e scaffolds required files and generation prompts; "
        "1e024a0 implements the app; e7b8303 adds security tests and fixes; 0f69a39 "
        "adds reproducible setup and recording guidance. Evidence and the report are "
        "committed separately after verification."
    )
    paragraph(
        "The recording follows this order: git clone, prompt overview, live prompt "
        "recreation in an empty workspace, security explanation, then functionality "
        "and limitations. The camera must be on initially and the narrated video must "
        "not exceed five minutes. SCREENCAST_SCRIPT.md supplies the exact commands "
        "and a target 4 minute 40 second narration."
    )
    paragraph(
        "Recording status: "
        + (
            recording
            if recording
            else "The student's live prompt replay, narrated recording, and unlisted YouTube upload remain to be completed."
        )
    )
    paragraph(
        "The replay helper copies only prompts and dependency files into a new temporary "
        "folder. It never copies app.py, templates, CSS, tests, a database, or a signing key. "
        "Newly generated code can differ and must be tested and demonstrated as produced."
    )
    heading("References")
    paragraph(
        "Assignment instructions: https://icardei.github.io/gensec-web/labs/G06.3_hw_wk6/index.html",
        size=11,
    )
    paragraph(
        "Instructor homework template: https://icardei.github.io/gensec-web/homework-template.docx",
        size=11,
    )
    paragraph(
        "Flask security guidance: https://flask.palletsprojects.com/en/stable/web-security/",
        size=11,
    )
    paragraph(
        "Werkzeug password hashing: https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security",
        size=11,
    )

    serialized = BytesIO()
    doc.save(serialized)
    serialized.seek(0)
    editable = {"word/document.xml", "word/_rels/document.xml.rels", "[Content_Types].xml"}
    with ZipFile(SOURCE) as baseline, ZipFile(serialized) as authored:
        with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as result:
            for name in baseline.namelist():
                result.writestr(
                    name, authored.read(name) if name in editable else baseline.read(name)
                )
            for name in authored.namelist():
                if name not in baseline.namelist():
                    assert name.startswith("word/media/"), name
                    result.writestr(name, authored.read(name))
    with ZipFile(SOURCE) as baseline, ZipFile(OUTPUT) as final:
        preserved = [name for name in baseline.namelist() if name not in editable]
        assert all(baseline.read(name) == final.read(name) for name in preserved)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    info = {
        "built_at": datetime.now(ZoneInfo("America/New_York")).isoformat(),
        "source_sha256": SOURCE_SHA,
        "preserved_package_parts": len(preserved),
        "recording_present": bool(recording),
        "output": OUTPUT.name,
    }
    (ROOT / "evidence/report-build.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
