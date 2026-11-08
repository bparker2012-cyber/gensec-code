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
    recording = (ROOT / "screencast_url.txt").read_text().strip()
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
    replace_text(27, "Application generation prompts")
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
        "Coding agent: OpenAI Codex, Codex desktop app. The saved prompts below "
        "describe the application and security checks used for the recorded generation.",
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

    prompts = (ROOT / "prompts.txt").read_text()
    first = prompts[prompts.index("PROMPT 1") : prompts.index("PROMPT 2")].strip().splitlines()
    second = prompts[prompts.index("PROMPT 2") : prompts.index("ACTUAL RECORDED REPLAY REQUEST")].strip().splitlines()
    heading("Prompt 1 Build the application")
    paragraph(" ".join(first[1:]))
    heading("Prompt 2 Verify security and prepare the demonstration")
    paragraph(" ".join(second[1:]))

    heading("Build prompt", new_page=True)
    picture(
        "21-vscode-build-prompt.png",
        "Figure 1. Application build prompt from prompts.txt, displayed in VS Code.",
    )
    heading("Build prompt continued", new_page=True)
    picture(
        "22-vscode-build-prompt-end.png",
        "Figure 2. Remaining lines of the application build prompt.",
    )

    heading("Verification prompt", new_page=True)
    picture(
        "23-vscode-verification-prompt.png",
        "Figure 3. Security verification prompt from prompts.txt, displayed in VS Code.",
    )

    heading("Additional generation request excerpt", new_page=True)
    picture(
        "12-vscode-replay-request.png",
        "Figure 4. Technical portion of the additional version and verification request.",
    )
    replay_request = (ROOT / "evidence/replay-request.txt").read_text()
    request_text = replay_request.split("Exact user message follows.\n\n", 1)[1]
    paragraph(request_text.split("\n\nDo not start the web server", 1)[0].strip(), size=10)

    heading("Generated application code", new_page=True)
    paragraph(
        "Codex generated app.py, Jinja templates, local CSS, locked dependencies, and "
        "security tests. The application supports registration, login, private notes, "
        "editing, deletion, and sign-out."
    )
    picture(
        "11-replay-generated-app.png",
        "Figure 5. Top lines of app.py in VS Code, with the FAU ID visible in the window title.",
    )

    heading("Security verification and agent replies", new_page=True)
    paragraph(
        "Codex reported 120 passing tests and 13 passing security checks. Locked "
        "installation, lock validation, lint, and formatting also passed."
    )
    picture(
        "13-vscode-replay-reply.png",
        "Figure 6. Final Codex reply from the recorded generation, showing the verification results.",
    )
    paragraph(
        "The suite covers unauthorized note access, missing or malformed CSRF tokens, "
        "stored XSS, SQL injection, password hashes, expired or revoked sessions, oversized "
        "inputs, host rejection, persistent signing keys, bounded state, and concurrent "
        "authentication attempts. The tests exercise real routes and SQLite."
    )

    heading("Generated verification code", new_page=True)
    paragraph(
        "The --demo command checks Flask routes and SQLite through the test client. "
        "It uses temporary test data and does not start a web server."
    )
    picture(
        "18-vscode-replay-demo.png",
        "Figure 7. Top lines of demo.py in VS Code, with the FAU ID visible.",
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
        "Figure 8. The note query includes the note ID and authenticated owner ID.",
    )

    heading("CSRF and authentication sessions", new_page=True)
    paragraph(
        "Every POST, including login, registration, and logout, verifies the session CSRF "
        "token. Registration, login, and logout replace the current browser's session "
        "and CSRF token. The previous session is revoked. The signed cookie contains "
        "only an opaque identifier; SQLite stores its hash and the CSRF token. Sessions "
        "expire after one hour. Cookies are HttpOnly and "
        "SameSite Strict; Secure cookies can be enabled when actual HTTPS is provided."
    )
    picture(
        "15-vscode-replay-csrf.png",
        "Figure 9. The request guard rejects duplicate fields and checks POST tokens.",
    )

    heading("Verification from a fresh GitHub clone", new_page=True)
    paragraph(
        "A fresh GitHub clone installed the locked dependencies and passed all 120 tests, "
        "all 13 demonstration checks, Ruff lint, and formatting. The output below comes "
        "from that check; the full command logs are saved under verification/."
    )
    paragraph((ROOT / "verification/final-clone-tests.txt").read_text().strip(), size=11)
    heading("Actual security demonstration output")
    p = paragraph((ROOT / "verification/final-clone-demo.txt").read_text().strip(), size=10)
    p.runs[0].font.name = "Liberation Mono"
    heading("Browser demonstration", new_page=True)
    paragraph(
        "Registration and note creation were checked in a browser using a temporary "
        "test account. The note reader displays the script-like input as text. The "
        "automated tests also cover reading, editing, deletion, and sign-out."
    )
    picture(
        "16-replay-notebook.jpg",
        "Figure 10. Test note with script-like input displayed as text and the FAU email visible in the footer.",
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
        "Figure 11. Registration page with the local HTTP and plaintext storage limitations visible.",
    )
    paragraph(
        "Current bounds include 120-character titles, 20,000-character note bodies, "
        "96 KiB requests, 1,024 live sessions, and 512 live rate-limit buckets. Each "
        "login and registration action allows eight credential submissions per peer IP "
        "and normalized account within a five-minute window. There is no total storage quota."
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
