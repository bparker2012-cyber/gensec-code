"""Validated Incident Compass tools. Brehon Parker, FAU ID Z23222679."""

import json
import re
import shlex
import subprocess
from pathlib import Path

from langchain.tools import tool
from pydantic import BaseModel, Field

DATA = Path(__file__).resolve().parent / "data"


@tool
def search_policy(query: str) -> str:
    """Search cited policy sections, returning no evidence for blank or unsupported requests."""
    no_evidence = "No matching policy evidence. I do not know."
    if not query.strip():
        return no_evidence
    terms = set(re.findall(r"\w+", query.lower())) - {
        "the", "a", "an", "is", "what", "when", "must", "be", "for", "to", "of",
    }
    sections = (DATA / "incident_policy.md").read_text().split("\n## ")[1:]
    severity = re.search(r"\bseverity\s+(\d+)\b", query, re.IGNORECASE)
    if severity:
        if severity.group(1) not in {"1", "2", "3"}:
            return no_evidence
        sections = [section for section in sections
                    if section.startswith(f"Severity {severity.group(1)}\n")]
    ranked = sorted(
        ((len(terms & set(re.findall(r"\w+", section.lower()))), section)
         for section in sections),
        key=lambda item: item[0], reverse=True,
    )
    matches = [f"[incident_policy.md: {section.splitlines()[0]}]\n{section}"
               for score, section in ranked if score > 0][:2]
    return "\n\n".join(matches) or no_evidence


class IncidentInput(BaseModel):
    """Explicit facts used by the deterministic classroom severity rules."""

    confirmed_data_loss: bool = Field(description="Confirmed exfiltration or data loss")
    ransomware: bool = Field(description="Confirmed ransomware")
    service_outage: bool = Field(description="Confirmed service outage")


@tool(args_schema=IncidentInput)
def triage_incident(confirmed_data_loss: bool, ransomware: bool, service_outage: bool) -> str:
    """Classify confirmed incident facts using the fictional classroom policy."""
    severity = 1 if confirmed_data_loss or ransomware else 2 if service_outage else 3
    return json.dumps({
        "severity": severity,
        "basis": "incident_policy.md",
        "next_steps": search_policy.invoke({"query": f"Severity {severity}"}),
        "limitation": "Rule-based classroom classification; does not verify supplied facts.",
    })


@tool
def Terminal(command: str) -> str:
    """Run only pwd, ls, or wc -l incident_policy.md in the classroom data folder.

    Shell expansion, command chaining, arbitrary paths, and write commands are rejected.
    """
    try:
        arguments = shlex.split(command)
    except ValueError:
        return "Rejected: malformed command."
    allowed = {("pwd",), ("ls",), ("wc", "-l", "incident_policy.md")}
    if tuple(arguments) not in allowed:
        return "Rejected: allowed commands are pwd, ls, and wc -l incident_policy.md."
    try:
        result = subprocess.run(
            arguments, cwd=DATA, shell=False, capture_output=True, text=True,
            timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Terminal failed: {type(exc).__name__}"
    return json.dumps({"command": arguments, "exit_code": result.returncode,
                       "stdout": result.stdout[:4000], "stderr": result.stderr[:1000]})


TOOLS = [search_policy, triage_incident, Terminal]
