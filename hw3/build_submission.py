"""Fill the course Word template while preserving all untouched package parts."""

import hashlib
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

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
            "credentials. Twelve offline tests pass. Live Gemini requires verification. "
            "Keyword retrieval can miss synonyms; triage depends on supplied facts; "
            "memory resets on exit."
        ),
        26: (
            'Task prompt: "new lab. '
            'https://icardei.github.io/gensec-web/labs/G03.2_hw_wk3/index.html?index=..%2F..gensec-web#0 '
            'do it ASAP." Required evidence: insert genuine VS Code screenshots '
            'of coding-agent prompts and responses, plus generated code, with '
            'Brehon Parker or Z23222679 visible.'
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
    print(output)


if __name__ == "__main__":
    main()
