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
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml.ns import qn
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
    replay = json.loads((ROOT / "evidence/replay-conversation.json").read_text())
    replay_replies = [m["text"].strip() for m in replay["messages"] if m["role"] == "assistant"]
    if recording:
        parsed = urlparse(recording)
        if parsed.scheme != "https" or parsed.hostname not in {
            "youtube.com",
            "www.youtube.com",
            "youtu.be",
            "loom.com",
            "www.loom.com",
        }:
            raise ValueError("Use the real HTTPS recording URL.")

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

    def link_value(index: int, url: str) -> None:
        run = original[index].runs[1]._r
        hyperlink = OxmlElement("w:hyperlink")
        relationship = doc.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
        hyperlink.set(qn("r:id"), relationship)
        run.getparent().replace(run, hyperlink)
        hyperlink.append(run)

    replace_text(2, "Homework Assignment no. 6")
    replace_text(5, "Student name: Brehon Parker")
    replace_text(7, "FAU Email: bparker2012@fau.edu")
    replace_value(18, recording or "Pending student recording")
    replace_value(20, " " + REPO)
    if recording:
        link_value(18, recording)
    link_value(20, REPO)
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
    second = prompts[prompts.index("PROMPT 2") : prompts.index("ACTUAL RECORDED REPLAY REQUEST")].strip().splitlines()
    heading("Prompt 1 Build the application")
    paragraph(" ".join(first[1:]))
    heading("Prompt 2 Verify security and prepare the demonstration")
    paragraph(" ".join(second[1:]))

    heading("Recorded replay request", new_page=True)
    paragraph(
        "The recorded Codex session read the two prompts above and regenerated the application. "
        "The following VS Code views show the exact additional request, including the fixed "
        "package versions, executable commands, and instruction to verify the result. "
        "The full visible conversation export is retained in evidence/replay-conversation.json."
    )
    picture(
        "12-vscode-replay-request.png",
        "Figure 2. Exact request from the recorded regeneration, displayed in VS Code with the FAU email visible.",
    )
    paragraph(replay_replies[0])

    heading("Recorded replay request continued", new_page=True)
    picture(
        "19-vscode-replay-request-end.png",
        "Figure 3. Remaining lines of the actual replay request. This is the continuation of Figure 2.",
    )
    paragraph(
        "The separate Codex chat worked in the course repository. It read the saved prompts, "
        "removed the preceding application source, and generated new source and tests inside "
        "hw6. The original implementation remains available in earlier Git commits. The "
        "regenerated application is preserved in commit cbb91a3868a6."
    )
    paragraph(
        "The standalone prompt file and the actual replay request have different roles: "
        "the former specifies the application, while the latter directs the recorded "
        "regeneration and verification. Both are retained in prompts.txt."
    )

    heading("Recorded replay request as text", new_page=True)
    paragraph(
        "Exact technical user message from the recorded regeneration, reproduced as "
        "ordinary selectable text in addition to Figures 2 and 3."
    )
    replay_request = (ROOT / "evidence/replay-request.txt").read_text()
    paragraph(replay_request.split("Exact user message follows.\n\n", 1)[1].strip(), size=11)

    heading("Generated application code", new_page=True)
    paragraph(
        "During the recorded replay, Codex generated app.py, local Jinja templates, CSS, "
        "a locked dependency environment, and security tests. The current source supports "
        "registration, note creation, reading, editing, deletion, and sign-out."
    )
    picture(
        "11-replay-generated-app.png",
        "Figure 4. Top lines of the regenerated Python application in VS Code, with bparker2012 visible in the window title.",
    )
    paragraph(
        "The source remains readable and divided into a small application factory, database "
        "helpers, authentication checks, and note routes. The UI requires no JavaScript or remote services."
    )

    heading("Security verification and agent replies", new_page=True)
    paragraph(
        "The recorded session reported 120 passing tests and 13 passing security checks. "
        "Locked installation, lock validation, lint, and formatting also passed. The "
        "image below displays the exact final reply from the conversation export."
    )
    picture(
        "13-vscode-replay-reply.png",
        "Figure 5. Exact final reply from the recorded Codex session, showing 120 passing tests and 13 passing security checks.",
    )
    paragraph(
        "The suite covers unauthorized note access, missing or malformed CSRF tokens, "
        "stored XSS, SQL injection, password hashes, expired or revoked sessions, oversized "
        "inputs, host rejection, persistent signing keys, bounded state, and concurrent "
        "authentication attempts. The tests exercise real routes and SQLite."
    )

    heading("Generated verification code", new_page=True)
    paragraph(
        "Codex added adversarial-input tests and a disposable demonstration. The --demo "
        "command calls actual Flask routes and SQLite through the test client. It uses "
        "temporary synthetic data and is separate from the live browser demonstration."
    )
    picture(
        "18-vscode-replay-demo.png",
        "Figure 6. Top lines of the regenerated in-process demonstration code, with the FAU ID visible.",
    )

    heading("Private note ownership", new_page=True)
    paragraph(
        "Every note lookup includes both the note ID and the authenticated user ID. "
        "Update and delete statements repeat the owner condition. A second account "
        "cannot list, open, edit, or delete the first account's note; these requests "
        "are covered by the passing test suite."
    )
    picture(
        "14-vscode-replay-owner.png",
        "Figure 7. The regenerated query binds both the note ID and the authenticated owner ID.",
    )

    heading("CSRF and authentication sessions", new_page=True)
    paragraph(
        "Every POST, including login, registration, and logout, verifies the session CSRF "
        "token. Authentication transitions clear session state and rotate the token. "
        "The signed cookie contains only an opaque session identifier. SQLite stores its "
        "hash and the CSRF token, allowing logout and subsequent login to revoke captured "
        "old cookies. Sessions have a fixed one-hour expiry. Cookies are HttpOnly and "
        "SameSite Strict; Secure cookies can be enabled when actual HTTPS is provided."
    )
    picture(
        "15-vscode-replay-csrf.png",
        "Figure 8. The regenerated request guard rejects duplicate fields and checks every POST token.",
    )

    heading("Verification from a fresh GitHub clone", new_page=True)
    receipt = json.loads((ROOT / "verification/final-clone-verification.json").read_text())
    paragraph(
        "A fresh clone of remote commit " + receipt["commit"][:12] + " installed the "
        "locked dependencies, passed all 120 tests, passed all 13 security demonstration "
        "checks, and passed Ruff lint and formatting checks. This independently verifies "
        "the regenerated source from GitHub. Receipts are retained under verification/."
    )
    paragraph((ROOT / "verification/final-clone-tests.txt").read_text().strip(), size=11)
    heading("Actual security demonstration output")
    p = paragraph((ROOT / "verification/final-clone-demo.txt").read_text().strip(), size=10)
    p.runs[0].font.name = "Liberation Mono"
    paragraph(
        "The original runtime dependency audit is retained under evidence/runs/ and covers "
        "the pinned runtime versions. The fresh-clone checks above establish the current "
        "test and demonstration results. These checks are not a complete security audit."
    )

    heading("Browser demonstration", new_page=True)
    paragraph(
        "The regenerated application was also exercised in a browser using a separate "
        "temporary database and synthetic account. Registration and note creation succeeded. "
        "The reader shows HTML-like input literally, and exposes edit and delete controls. "
        "The full create/read/edit/delete and sign-out flow is covered by the passing tests "
        "and the student's recorded demonstration."
    )
    picture(
        "16-replay-notebook.jpg",
        "Figure 9. The regenerated notebook with synthetic note content, escaped script-like text, and the FAU email in the footer.",
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
        "17-replay-registration.jpg",
        "Figure 10. The regenerated registration page identifies the local classroom mode and plaintext storage limits.",
    )
    paragraph(
        "Current bounds include 120-character titles, 20,000-character note bodies, "
        "96 KiB requests, 1,024 live sessions, and 512 live rate-limit buckets. Each "
        "authentication action permits eight attempts per peer IP and normalized account "
        "within a fixed five-minute window. There is no total storage quota."
    )

    serialized = BytesIO()
    doc.save(serialized)
    serialized.seek(0)
    editable = {"word/document.xml", "word/_rels/document.xml.rels", "[Content_Types].xml"}
    with ZipFile(SOURCE) as baseline, ZipFile(serialized) as authored:
        with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as result:
            for name in baseline.namelist():
                content = authored.read(name) if name in editable else baseline.read(name)
                if name == "word/settings.xml":
                    content = content.replace(
                        b"</w:settings>",
                        b'<w:updateFields w:val="true"/></w:settings>',
                    )
                result.writestr(name, content)
            for name in authored.namelist():
                if name not in baseline.namelist():
                    assert name.startswith("word/media/"), name
                    result.writestr(name, authored.read(name))
    with ZipFile(SOURCE) as baseline, ZipFile(OUTPUT) as final:
        preserved = [
            name for name in baseline.namelist()
            if name not in editable and name != "word/settings.xml"
        ]
        assert all(baseline.read(name) == final.read(name) for name in preserved)
        assert final.read("word/settings.xml") == baseline.read("word/settings.xml").replace(
            b"</w:settings>", b'<w:updateFields w:val="true"/></w:settings>'
        )
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    info = {
        "built_at": datetime.now(ZoneInfo("America/New_York")).isoformat(),
        "source_sha256": SOURCE_SHA,
        "preserved_package_parts": len(preserved),
        "settings_change": "Only updateFields true added so Word refreshes page fields on open.",
        "recording_present": bool(recording),
        "output": OUTPUT.name,
    }
    (ROOT / "evidence/report-build.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
