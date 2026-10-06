"""Fill the course Word template while preserving all untouched package parts."""

import hashlib
from pathlib import Path
from zipfile import ZipFile

from lxml import etree
from docx import Document
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parent
REFERENCE = Path("/tmp/hw3-homework-template.docx")
EXPECTED = "fbaa32ec1280231827a314eb95ac7c6b5ad55f4c5ffc5b8d666d3b867b486763"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def main():
    """Fill known fields and leave explicit spaces for required human evidence."""
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == EXPECTED
    values = {
        2: "Homework Assignment no. 3",
        5: "Student name: Brehon Parker   FAU ID: Z23222679",
        16: "Screencast Recording URL: PENDING RECORDING",
        18: "Github Repository URL: https://github.com/bparker2012-cyber/gensec-code",
        20: "Application name: Incident Compass",
        22: (
            "Application Description: Incident Compass adds cited policy search, "
            "validated incident triage, and a restricted Terminal to a stateful "
            "LangChain agent. It uses fictional classroom policy and environment "
            "credentials. Fifteen offline tests pass. Live Gemini via Vertex AI "
            "successfully invoked Terminal and policy search on 2026-10-06. "
            "Keyword retrieval can miss synonyms; triage depends on supplied facts; "
            "memory resets on exit."
        ),
        26: (
            'Development evidence: The following pages document genuine follow-up '
            'development using the Codex agent in VS Code. Initial implementation '
            'was performed in Codex desktop, so this evidence does not claim that '
            'every original development task was performed in VS Code.'
        ),
    }
    output = ROOT / "hw3-Z23222679.docx"
    with ZipFile(REFERENCE) as source, ZipFile(output, "w") as target:
        for entry in source.infolist():
            content = source.read(entry.filename)
            if entry.filename == "word/document.xml":
                root = etree.fromstring(content)
                paragraphs = root.findall("w:body/w:p", NS)
                for index, text in values.items():
                    nodes = paragraphs[index].findall(".//w:t", NS)
                    nodes[0].text = text
                    for node in nodes[1:]:
                        node.text = ""
                content = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
            target.writestr(entry, content)
    with ZipFile(REFERENCE) as source, ZipFile(output) as target:
        assert all(source.read(name) == target.read(name)
                   for name in source.namelist() if name != "word/document.xml")
    document = Document(output)
    original_count = len(document.paragraphs)
    document.add_page_break()
    document.add_paragraph().add_run("VS Code Development Evidence").bold = True
    prompt = (
        "Brehon Parker / FAU ID Z23222679 / Homework 3. In hw3/tools.py, fix "
        "search_policy so a request for an unsupported explicit severity such as "
        "Severity 4 returns no policy evidence instead of unrelated Severity 1/2/3 "
        "sections. Add focused tests for unsupported severity and empty search "
        "queries in hw3/tests/test_agent.py; treat empty queries as no evidence. "
        "Preserve the existing tools, Terminal restrictions, and unrelated files. "
        "Use docstrings, run uv run pytest -q in hw3, and summarize the exact change "
        "and test result. Do not commit or push."
    )
    document.add_paragraph("Exact prompt: " + prompt)
    document.add_paragraph("Agent response and task result: 15 tests passed; unsupported severities and blank queries return no evidence.")
    document.add_picture(str(ROOT / "evidence/vscode-prompt-response.png"), width=Inches(6.6))
    document.add_page_break()
    document.add_paragraph().add_run("Generated and Modified Code").bold = True
    document.add_paragraph("Brehon Parker / FAU ID Z23222679. Actual VS Code source view showing the modified search_policy function. Name/ID header added for attribution after the agent task.")
    document.add_picture(str(ROOT / "evidence/vscode-code.png"), width=Inches(6.6))
    for paragraph in document.paragraphs[original_count:]:
        for run in paragraph.runs:
            run.font.size = Pt(10)
    document.save(output)
    print(output)


if __name__ == "__main__":
    main()
