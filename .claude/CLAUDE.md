# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent AI system (Python port of TypeScript charisma-agency-poc) with 6 specialized agents built on LangChain, LangGraph, and deepagents. Includes an autonomous optimization loop (autoresearch) for agent001.

## Commands

```bash
uv sync                                    # Install dependencies (use uv, not pip)
uv run langgraph dev                       # Start LangGraph dev server (http://localhost:2024)
uv run python -m autoresearch.eval         # Evaluate agent001 against 20 test cases
uv run python -m autoresearch.loop         # Run autoresearch optimization loop
uv run python tests/test_agents_playwright.py  # E2E tests (requires dev server running)
```

## Architecture

### Agent Patterns

Three agent construction patterns are used:

1. **StateGraph** (agent001): Custom graph with explicit state, `llm_call` and `tool_node` nodes, manual routing logic. Used for complex workflows.
2. **ReAct** (agent002, agent003): LangGraph prebuilt `create_react_agent`. Simpler tool-use loops.
3. **deepagents** (agent004, agent005, agent007): `create_deep_agent` with support for memory, subagents, `LocalShellBackend`, and complex workflows.

### Agents

| Agent | Role | Tools/Integration |
|-------|------|-------------------|
| agent001 | Arithmetic (autoresearch target) | Custom math tools, StateGraph |
| agent002 | Weather (minimal example) | Static get_weather, ReAct |
| agent003 | Holiday Request Assistant | MCP tools (HCM backend), ReAct |
| agent004 | Expert Research | Tavily internet_search, deepagents |
| agent005 | File Management | LocalShellBackend + filesystem tools + researcher subagent |
| agent007 | Bridge Holiday Planner | MCP tools + internet_search, deepagents |

### MCP Integration

Agents 003 and 007 connect to HCM backend MCP servers (Holiday Request, Employee Profile, Workflow) via `langchain-mcp-adapters`. These require running .NET Aspire services and dev credentials in `.env.local`.

### Autoresearch System

Autonomous optimization loop for agent001:
- Evaluates against 20 arithmetic test cases (`autoresearch/dataset.json`)
- OpenAI optimizer proposes code changes to `src/agent001/agent.py`
- Scores improvements (1% relative tolerance), commits if better, reverts if worse
- History tracked in `autoresearch/results.tsv`

## Configuration

- `langgraph.json`: Agent graph definitions (maps agent names to Python modules)
- `.env.local`: API keys and MCP URLs (copy from `.env.example`)
- `.mcp.json`: MCP server configs (Playwright, docs, Context7)

Required env vars: `OPENAI_API_KEY`. Optional: `TAVILY_API_KEY` (agents 004/005/007), `LANGSMITH_API_KEY` (tracing), MCP URLs (agents 003/007).

## Key Conventions

- All agents are exposed as LangGraph graphs via `langgraph.json` and follow the pattern `src.<agentN>.agent:agent`
- System prompts for complex agents live in dedicated `system_prompt.py` files
- MCP tool loading is in `tools/mcp_tools.py` within each agent that uses it
- Agent005 workspace is sandboxed to `src/agent005/workspace/`
- Python 3.11+, uses type hints and Pydantic models
