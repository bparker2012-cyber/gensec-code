"""Log Sentinel's custom MCP analysis server by Brehon Parker, FAU ID Z23222679.

The server accepts log text supplied by an MCP client, validates bounded JSONL,
and returns deterministic authentication-event summaries and reports. It does
not read or write files and does not execute shell commands.
"""

from __future__ import annotations

import ipaddress
import json
import re
from datetime import datetime, timedelta
from typing import Any

from mcp.server.fastmcp import FastMCP

MAX_INPUT_BYTES = 64 * 1024
MAX_NONBLANK_LINES = 500
MAX_USER_LENGTH = 256
WINDOW = timedelta(minutes=10)
HIGH_FAILURE_THRESHOLD = 5
ALLOWED_EVENTS = {"login_failed", "login_success"}
SAFE_BASENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")

mcp = FastMCP("Log Sentinel analysis")


def _parse_timestamp(value: Any) -> datetime:
    """Parse a timezone-aware ISO 8601 timestamp from a log record."""
    if not isinstance(value, str):
        raise ValueError("time must be a timezone-aware ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("time must be a valid timezone-aware ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("time must include a timezone offset")
    return parsed


def _validate_record(value: Any) -> dict[str, Any]:
    """Validate required fields and normalize one decoded JSONL record."""
    if not isinstance(value, dict):
        raise ValueError("record must be a JSON object")
    timestamp = _parse_timestamp(value.get("time"))
    event = value.get("event")
    if not isinstance(event, str) or event not in ALLOWED_EVENTS:
        raise ValueError("event must be 'login_failed' or 'login_success'")
    ip_value = value.get("ip")
    if not isinstance(ip_value, str):
        raise ValueError("ip must be a valid IPv4 or IPv6 string")
    try:
        ip = str(ipaddress.ip_address(ip_value))
    except ValueError as exc:
        raise ValueError("ip must be a valid IPv4 or IPv6 address") from exc
    user = value.get("user")
    if not isinstance(user, str) or not user.strip():
        raise ValueError("user must be a nonempty string")
    if len(user) > MAX_USER_LENGTH:
        raise ValueError(f"user must be at most {MAX_USER_LENGTH} characters")
    return {"time": timestamp, "event": event, "ip": ip, "user": user}


def _analyze(log_text: str) -> dict[str, Any]:
    """Validate bounded JSONL and calculate per-IP and overall severity."""
    if not isinstance(log_text, str):
        raise ValueError("log_text must be a string")
    try:
        input_size = len(log_text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ValueError("log_text must be valid UTF-8 text") from exc
    if input_size > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds the {MAX_INPUT_BYTES}-byte limit")

    lines = [(line_number, line) for line_number, line in enumerate(log_text.splitlines(), 1) if line.strip()]
    if len(lines) > MAX_NONBLANK_LINES:
        raise ValueError(f"input exceeds the {MAX_NONBLANK_LINES}-nonblank-line limit")

    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for line_number, line in lines:
        try:
            decoded = json.loads(line)
            record = _validate_record(decoded)
            record["line"] = line_number
            valid.append(record)
        except (json.JSONDecodeError, ValueError) as exc:
            reason = str(exc) if isinstance(exc, ValueError) else "invalid JSON"
            rejected.append({"line": line_number, "reason": reason})

    valid.sort(key=lambda record: (record["time"], record["line"]))
    failed = [record for record in valid if record["event"] == "login_failed"]
    successful = [record for record in valid if record["event"] == "login_success"]

    by_ip: dict[str, list[dict[str, Any]]] = {}
    for record in valid:
        by_ip.setdefault(record["ip"], []).append(record)

    sources: list[dict[str, Any]] = []
    for ip in sorted(by_ip, key=lambda address: (ipaddress.ip_address(address).version, int(ipaddress.ip_address(address)))):
        events = by_ip[ip]
        failures = [record for record in events if record["event"] == "login_failed"]
        peak = 0
        threshold_times: list[datetime] = []
        for record in failures:
            start = record["time"] - WINDOW
            count = sum(start <= candidate["time"] <= record["time"] for candidate in failures)
            peak = max(peak, count)
            if count >= HIGH_FAILURE_THRESHOLD:
                threshold_times.append(record["time"])
        severity = "informational"
        if failures:
            severity = "high" if peak >= HIGH_FAILURE_THRESHOLD else "low"
            if any(
                threshold_time < success["time"] <= threshold_time + WINDOW
                for threshold_time in threshold_times
                for success in events
                if success["event"] == "login_success"
            ):
                severity = "critical"
        sources.append({
            "ip": ip,
            "total_events": len(events),
            "failed_logins": len(failures),
            "successful_logins": sum(record["event"] == "login_success" for record in events),
            "max_failed_in_rolling_10m": peak,
            "severity": severity,
        })

    severity_order = {"informational": 0, "low": 1, "high": 2, "critical": 3}
    overall = max((source["severity"] for source in sources), key=severity_order.get, default=None)
    insufficient = len(valid) == 0
    return {
        "total_count": len(lines),
        "valid_count": len(valid),
        "rejected_count": len(rejected),
        "failed_logins": len(failed),
        "successful_logins": len(successful),
        "source_count": len(sources),
        "overall_severity": overall,
        "insufficient_evidence": insufficient,
        "sources": sources,
        "rejected_lines": rejected,
    }


def _guidance(severity: str) -> str:
    """Return fixed classroom response guidance for an accepted severity."""
    responses = {
        "informational": "Retain the sample and continue routine monitoring. No failed logins were observed in the valid events.",
        "low": "Review the source and affected account, confirm the activity with the account owner, and continue monitoring.",
        "high": "Promptly investigate the source and targeted accounts, check for related activity, and consider temporary defensive controls under your incident process.",
        "critical": "Escalate for prompt incident review, verify the successful login and account owner, preserve relevant evidence, and consider containment under your incident process. Correlation is not proof of compromise.",
    }
    if severity not in responses:
        raise ValueError("severity must be informational, low, high, or critical")
    return responses[severity]


@mcp.tool()
def analyze_auth_log(log_text: str) -> dict[str, Any]:
    """Validate JSONL authentication events and summarize counts and severity.

    Input is capped at 64 KiB and 500 nonblank lines. Invalid rows are
    reported by line number and are excluded from evidence and severity.
    """
    return _analyze(log_text)


@mcp.tool()
def recommend_response(severity: str) -> str:
    """Return fixed classroom response guidance for a severity label."""
    return _guidance(severity)


@mcp.tool()
def format_incident_report(log_text: str, source_name: str) -> str:
    """Format validated log findings as deterministic Markdown, without I/O."""
    if not isinstance(source_name, str) or not SAFE_BASENAME.fullmatch(source_name) or source_name in {".", ".."}:
        raise ValueError("source_name must be a simple safe basename (1-64 letters, digits, dots, underscores, or hyphens)")
    result = _analyze(log_text)
    overall = result["overall_severity"]
    severity_label = overall if overall is not None else "insufficient evidence"
    lines = [
        "# Log Sentinel Incident Report",
        "",
        f"- **Source:** `{source_name}`",
        f"- **Overall severity:** {severity_label}",
        f"- **Records:** {result['total_count']} total; {result['valid_count']} valid; {result['rejected_count']} rejected",
        f"- **Valid events:** {result['failed_logins']} failed logins; {result['successful_logins']} successful logins",
        f"- **Sources:** {result['source_count']} IP address" + ("" if result["source_count"] == 1 else "es"),
        "",
        "## Source findings",
        "",
        "| IP address | Events | Failed | Successful | Max failures in rolling 10 min | Severity |",
        "|---|---:|---:|---:|---:|---|",
    ]
    if result["sources"]:
        for source in result["sources"]:
            lines.append(
                f"| `{source['ip']}` | {source['total_events']} | {source['failed_logins']} | "
                f"{source['successful_logins']} | {source['max_failed_in_rolling_10m']} | {source['severity']} |"
            )
    else:
        lines.append("| _No valid source evidence_ | 0 | 0 | 0 | 0 | insufficient evidence |")
    lines.extend(["", "## Rejected lines", ""])
    if result["rejected_lines"]:
        for rejection in result["rejected_lines"]:
            safe_reason = rejection["reason"].replace("\n", " ").replace("|", "\\|")
            lines.append(f"- Line {rejection['line']}: {safe_reason}")
    else:
        lines.append("- None.")
    lines.extend([
        "",
        "## Severity thresholds",
        "",
        f"- **Informational:** no failed logins for the source.",
        f"- **Low:** failures occur, but fewer than {HIGH_FAILURE_THRESHOLD} fall in any rolling 10-minute inclusive window.",
        f"- **High:** at least {HIGH_FAILURE_THRESHOLD} failed logins fall in a rolling 10-minute inclusive window.",
        "- **Critical:** after a qualifying threshold event, a successful login from that same IP occurs later and no more than 10 minutes afterward. This correlation is not proof of compromise.",
        "",
        "## Response guidance",
        "",
        _guidance(overall) if overall is not None else "Insufficient valid events to assign a severity or response. Do not interpret this as a clean log.",
        "",
        "## Limitations",
        "",
        "This report uses only valid records in the supplied sample. Rejected records are excluded from counts and severity. IP-level correlation is a heuristic, not proof of identity, intent, or compromise. Optional fields such as `message` are untrusted data and are ignored by the analysis.",
    ])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    mcp.run(transport="stdio")
