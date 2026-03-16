# Charisma Agency (Python)

An AI agency built with LangChain and LangGraph that exposes specialized agents like arithmetic, weather, HCM holiday requests (via MCP), internet research, and file management. This is the Python port of the [TypeScript original](https://github.com/osstotalsoft/charisma-agency-poc).

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Create a `.env.local` file with your OpenAI API key:
   ```env
   OPENAI_API_KEY=your-api-key
   OPENAI_MODEL=gpt-4o-mini  # optional, defaults to gpt-4o-mini
   ```

## Running

Start the LangGraph dev server:

```bash
uv run langgraph dev
```

The server will be available at `http://localhost:2024`.

## Agent Chat UI

You can interact with the agent using [Agent Chat UI](https://agentchat.vercel.app/?apiUrl=http://localhost:2024&assistantId=agent001).

## Agents

### agent001

A simple agent that performs arithmetic operations using a custom StateGraph with an LLM call node and tool execution node that loops until no more tools are needed.

Tools:

- **add** — adds two numbers
- **multiply** — multiplies two numbers
- **divide** — divides two numbers

### agent002

A minimal weather agent built with LangGraph's prebuilt ReAct agent. Uses a single `get_weather` tool that returns a static sunny forecast for any city.

### agent003

A Holiday Request Assistant that connects to HCM backend services via MCP (Model Context Protocol) over SSE. Helps users view and create holiday requests through a guided multi-step workflow.

Tools (loaded from MCP servers):

- **get_my_holiday_requests** — fetch the current user's holiday requests
- **get_reasons_left** — fetch available leave reason types
- **get_employees_for_func_tag** — fetch replacement employee candidates
- **create_holiday_request** — submit a new holiday request
- **get_holiday_request** — retrieve a request by workflow instance ID

Requires `HOLIDAY_REQUEST_MCP_URL` and `EMPLOYEE_PROFILE_MCP_URL` env vars pointing to the HCM MCP servers. For local development, set `DEV_TENANT_ID`, `DEV_USER_PASSPORT`, `DEV_AUTHORIZATION`, and `DEV_LANGUAGE` (copy from browser Network tab after HCM login).

### agent004

An expert research agent built with the `deepagents` library. Conducts thorough research and writes polished reports using an internet search tool powered by Tavily.

Requires a `TAVILY_API_KEY` env var.

### agent005

A File Management Assistant built with the `deepagents` library. Helps users explore, read, create, edit, and search files in a sandboxed workspace directory (`src/agent005/workspace/`).

Tools (provided by `LocalShellBackend`):

- **ls** — list files and directories
- **read_file** — read file contents
- **write_file** — create or overwrite files
- **edit_file** — make targeted edits to existing files
- **glob** — find files matching patterns
- **grep** — search file contents with regex patterns
- **execute** — run shell commands in the workspace

Also supports persistent memory via `/MEMORY.md` and self-updating user preferences.

### agent007

An enhanced agent that combines MCP tools with internet research capabilities. Built with the `deepagents` library, it integrates dynamically loaded MCP tools alongside Tavily-powered internet search.

Requires `TAVILY_API_KEY` and the same MCP env vars as agent003.

## Autoresearch: Autonomous Agent Optimization

An autonomous optimization loop inspired by [hwchase17/autoresearch-agents](https://github.com/hwchase17/autoresearch-agents). An LLM "optimizer" (GPT-4o) continuously improves `agent001` by proposing code changes, evaluating them against a test suite, and keeping only improvements.

### How it works

1. The optimizer reads the current `src/agent001/agent.py` and past results
2. It proposes a new version of the file (adding tools, improving prompts, etc.)
3. The new code is syntax-checked, then evaluated against 20 arithmetic test cases
4. If the score improves, the change is committed; otherwise it's reverted
5. Repeats until the score reaches 1.0 or 20 iterations are exhausted

### Run the evaluation only

```bash
uv run python -m autoresearch.eval
```

Outputs a JSON report with per-case scores and an aggregate score.

### Run the optimization loop

```bash
uv run python -m autoresearch.loop
```

This will iteratively improve `agent001`, printing progress and keeping a log in `autoresearch/results.tsv`. Check `git log` to see committed improvements.
