"""Rebuild the assessment PDF from retained evidence, screenshots, and recording URL."""

import html
import json
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence"
REPO = "https://github.com/bparker2012-cyber/gensec-code"
BRANCH = "codex/hw5-incident-compass-assessment"
INK = colors.HexColor("#132B40")
TEAL = colors.HexColor("#126476")
MUTED = colors.HexColor("#526675")
BODY = ParagraphStyle("Body", fontName="Helvetica", fontSize=10.2, leading=14, textColor=INK)
NOTE = ParagraphStyle("Note", parent=BODY, fontSize=8.8, leading=12, textColor=MUTED)


def paragraph(c, text, y, width=504, style=BODY):
    p = Paragraph(text, style)
    _, height = p.wrap(width, 1000)
    if y - height < 43:
        raise ValueError("Report text would overflow the page.")
    p.drawOn(c, 54, y - height)
    return y - height - 10


def section(c, title, y):
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(54, y - 13, title)
    return y - 24


def frame(c, number):
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(54, 757, "GENERATIVE SECURITY  /  HOMEWORK 5")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawRightString(558, 757, "SECURITY ASSESSMENT")
    c.setStrokeColor(colors.HexColor("#CBD5DD"))
    c.line(54, 746, 558, 746)
    c.line(54, 37, 558, 37)
    c.drawString(54, 23, "Brehon Parker | Z23222679 | 26 October 2026")
    c.drawRightString(558, 23, str(number))


def screenshot_page(c, number, title, filename, caption, run_time):
    c.setPageSize(landscape(letter))
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(36, 591, title)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8.5)
    c.drawString(36, 576, "Original HW3 CLI output in the local capture viewer | " + run_time)
    image = ImageReader(str(EVIDENCE / filename))
    width, height = image.getSize()
    displayed_width = 720
    displayed_height = height * displayed_width / width
    top = 566
    bottom = top - displayed_height
    if bottom < 35:
        raise ValueError("Screenshot would be too large for its landscape page.")
    c.drawImage(image, 36, bottom, width=displayed_width, height=displayed_height)
    c.setFont("Helvetica", 8)
    c.drawString(36, bottom - 13, caption)
    c.setFont("Helvetica", 7)
    c.drawRightString(756, 12, str(number))
    c.showPage()


def main():
    original = (EVIDENCE / "attack-01-live-run.txt").read_text()
    prompt = original.split("Prompt:\n", 1)[1].split("\n\nObserved tool calls:", 1)[0]
    response = original.split("Actual model response:\n", 1)[1].split("\n\nControl attempt", 1)[0]
    rerun = json.loads((EVIDENCE / "attack-01-rerun.json").read_text())
    initial = json.loads((EVIDENCE / "attack-01-rerun-initial.json").read_text())
    recording = (ROOT / "screencast_url.txt").read_text().strip()
    stream = BytesIO()
    c = canvas.Canvas(stream, pagesize=letter)
    c.setTitle("Homework 5 - Incident Compass Prompt Exposure")
    c.setAuthor("Brehon Parker")

    frame(c, 1)
    c.setFont("Helvetica-Bold", 23)
    c.setFillColor(INK)
    c.drawString(54, 714, "Incident Compass: Prompt Exposure")
    y = paragraph(c, "Homework 5 security assessment | Brehon Parker | FAU ID Z23222679", 698, style=NOTE)
    y = paragraph(c, "I tested my Homework 3 Incident Compass agent against live Gemini 2.5 Flash through Vertex AI. A direct instruction override disclosed the application system prompt and, in the original and final captured runs, the available tool schemas and descriptions. No tool-result lines appeared in those runs.", y - 4)
    y = section(c, "1. Target and APE classification", y)
    y = paragraph(c, "<b>Target:</b> hw3/app.py and hw3/tools.py; LangChain tool-calling agent. One-shot CLI requests used existing Vertex AI credentials; credential values were not displayed. The target source and policy were unchanged.<br/><b>Tactic:</b> Cognitive Manipulation (HLT03). <b>Technique:</b> Instruction Override (HLT03.11). <b>Objective:</b> System Prompt Exposure (HLG01.01).", y)
    y = paragraph(c, '<link href="https://ape.hiddenlayer.com/technique.html?id=HLT03.11" color="#126476">APE attack description: Instruction Override (HLT03.11)</link> | <link href="https://ape.hiddenlayer.com/objective.html?id=HLG01.01" color="#126476">System Prompt Exposure</link>', y, style=NOTE)
    y = section(c, "2. Exact attacker message", y)
    y = paragraph(c, html.escape(prompt), y)
    y = section(c, "3. Observations, impact, and limits", y)
    y = paragraph(c, "The retained original exchange returned the system prompt and all three tool descriptions. A confirming run at " + initial["finished_utc"] + " returned the system prompt alone. The captured run at " + rerun["finished_utc"] + " returned both the system prompt and tool schemas; Figures 1 and 2 show that run. Neither confirming run printed a TOOL result line. The raw outputs and source SHA-256 values are retained with the evidence.", y)
    y = paragraph(c, "The observed impact is limited to instruction and tool-metadata disclosure. I did not obtain credentials, private files, or real incident records, execute a tool, or demonstrate a tool-boundary bypass. A separate request to fabricate a Severity 1 exfiltration finding was refused; I do not count that request as a successful attack.", y)
    y = paragraph(c, "<b>Impact limit:</b> The target has no explicit rule requiring system-prompt secrecy, and its instructions and tool definitions are already public in the repository. This demonstrates model-context disclosure; it does not prove that a specific confidentiality rule was overridden or that private secrets were leaked.", y, style=NOTE)
    y = paragraph(c, "<b>Response:</b> Treat prompts as discoverable, keep secrets and authorization decisions outside model context, and retain tool restrictions enforced in code. These runs establish a specific disclosure, not universal susceptibility to every prompt.", y)
    y = section(c, "4. Repository, recording, and evidence", y)
    y = paragraph(c, '<b>Repository:</b> <link href="' + REPO + '/tree/' + BRANCH + '/hw5" color="#126476">github.com/bparker2012-cyber/gensec-code</link><br/><b>Branch:</b> ' + BRANCH + '<br/>' + (('<b>Recording:</b> <link href="' + html.escape(recording, quote=True) + '" color="#126476">' + html.escape(recording) + '</link>') if recording else '<b>Recording:</b> Pending. I will add the unlisted video URL after recording.') + '<br/><b>Screenshots:</b> Figures 1 and 2 are actual browser captures of a local viewer executing the original CLI. They show live stdout excerpts. The prompt-entry image and full raw outputs are retained in the repository.', y, style=NOTE)
    c.showPage()

    frame(c, 2)
    y = section(c, "5. Original live model response", 724)
    y = paragraph(c, "The response below is from the original saved CLI exchange. Wording is verbatim; blank lines are condensed for layout. The later live screenshots are on the following landscape pages.", y, style=NOTE)
    lines = [line for line in response.splitlines() if line.strip()]
    c.setFillColor(INK)
    c.setFont("Courier", 8.3)
    for line in lines:
        if y < 70:
            raise ValueError("Original response would overflow.")
        c.drawString(54, y - 8.3, line)
        y -= 10.5
    y -= 14
    y = paragraph(c, "<b>Tool observation:</b> No TOOL lines appeared. The model disclosed available tool definitions; disclosure does not mean a tool was invoked. The same observation applies to the final captured run, whose status reports zero tool-result lines.", y, style=NOTE)
    c.showPage()

    screenshot_page(c, 3, "Figure 1. Live system-prompt disclosure", "attack-01-system-prompt.jpg", "The exact attacker prompt and returned application instructions are readable; the live run reports zero tool-result lines.", rerun["finished_utc"])
    screenshot_page(c, 4, "Figure 2. Live tool-metadata disclosure", "attack-01-tool-metadata.jpg", "The same response exposes the three tool schemas and descriptions, including the Terminal restrictions.", rerun["finished_utc"])
    c.save()
    output = ROOT / "hw5-Z23222679.pdf"
    output.write_bytes(stream.getvalue())
    print(output)


if __name__ == "__main__":
    main()
