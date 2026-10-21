# Log Sentinel

Homework 4 scaffold by Brehon Parker (FAU ID Z23222679).

Log Sentinel is planned as a security log analysis MCP agent. This repository
contains project scaffolding only; the agent and custom MCP server have not
been implemented.

## Planned design

1. The published `@modelcontextprotocol/server-filesystem` MCP server reads
   sample log files from an explicitly configured directory.
2. A custom MCP server analyzes failed login activity and scores incidents.
3. A LangChain agent coordinates both MCP servers, summarizes the findings,
   and writes an analysis report.

## Project files

- `agent.py`: future LLM/MCP orchestration entry point.
- `mcp-server.py`: future custom log-analysis MCP server entry point.
- `screencast_url.txt`: submission URL placeholder.
- `.env.example`: placeholder for required environment configuration.

Dependencies and runtime requirements are declared in `pyproject.toml` and
`package.json`. No analysis or report generation is available yet.
