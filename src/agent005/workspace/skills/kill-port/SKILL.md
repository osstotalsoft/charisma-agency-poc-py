---
name: kill-port
description: Kill processes running on a specific port
---

# kill-port

Use the `execute` tool to run `npx kill-port <port>` to terminate any process listening on the given port.

## Usage

When the user asks to kill, stop, or free a port:

1. Run `npx kill-port <port>` via the `execute` tool.
2. Report whether it succeeded.

## Examples

- "Kill port 3000" → `execute("npx kill-port 3000")`
- "Free up port 8080" → `execute("npx kill-port 8080")`
- "Stop whatever is running on port 4200" → `execute("npx kill-port 4200")`
