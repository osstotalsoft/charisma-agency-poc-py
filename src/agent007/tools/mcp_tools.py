import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

REQUIRED_TOOLS = [
    "get_my_holiday_requests",
    "create_holiday_request",
    "get_holiday_request",
    "get_employees_for_func_tag",
]


@dataclass
class UserContext:
    tenant_id: Optional[str] = None
    user_passport: Optional[str] = None
    authorization: Optional[str] = None
    language: Optional[str] = None


@dataclass
class McpToolsResult:
    tools: dict[str, Any] = field(default_factory=dict)
    cleanup: Any = None


def _make_stub(name: str) -> StructuredTool:
    """Create a stub tool that returns an error message."""
    return StructuredTool.from_function(
        func=lambda: f"Error: MCP tool {name} is not available",
        name=name,
        description=f"Stub: {name} — MCP server not available",
    )


def _make_empty_tools() -> dict[str, Any]:
    return {name: _make_stub(name) for name in REQUIRED_TOOLS}


async def load_mcp_tools(user_context: UserContext) -> McpToolsResult:
    """Load MCP tools from holiday-request and employee-profile servers."""
    headers: dict[str, str] = {}

    if user_context.tenant_id:
        headers["Tenant-Id"] = user_context.tenant_id

    if user_context.user_passport:
        try:
            passport = json.loads(user_context.user_passport)
            user_id = passport.get("UserId") or passport.get("userId")
            if user_id:
                headers["User-Id"] = str(user_id)
        except (json.JSONDecodeError, TypeError):
            pass  # non-critical

        # Escape non-ASCII (Romanian diacritics) as \uXXXX — HTTP headers must be Latin-1.
        headers["User-Passport"] = re.sub(
            r"[\x80-\uffff]",
            lambda m: f"\\u{ord(m.group()):04x}",
            user_context.user_passport,
        )

    if user_context.authorization:
        headers["Authorization"] = user_context.authorization
    if user_context.language:
        headers["Accept-Language"] = user_context.language

    server_configs: dict[str, dict] = {}

    holiday_url = os.environ.get("HOLIDAY_REQUEST_MCP_URL")
    if holiday_url:
        server_configs["hcm-holiday-request"] = {
            "transport": "sse",
            "url": f"{holiday_url}/sse",
            "headers": headers,
        }

    employee_url = os.environ.get("EMPLOYEE_PROFILE_MCP_URL")
    if employee_url:
        server_configs["hcm-employee-profile"] = {
            "transport": "sse",
            "url": f"{employee_url}/sse",
            "headers": headers,
        }

    if not server_configs:
        logger.warning(
            "No MCP server URLs configured for bridge-planner-agent — skipping MCP tool loading"
        )
        return McpToolsResult(tools=_make_empty_tools(), cleanup=None)

    try:
        client = MultiServerMCPClient(server_configs)
        all_tools = await client.get_tools()

        tool_map = {t.name: t for t in all_tools if t.name in REQUIRED_TOOLS}

        missing = [name for name in REQUIRED_TOOLS if name not in tool_map]
        if missing:
            logger.warning(
                "bridge-planner-agent: missing expected MCP tools: %s",
                ", ".join(missing),
            )

        logger.info(
            "bridge-planner-agent MCP tools loaded: %s",
            ", ".join(tool_map.keys()),
        )

        return McpToolsResult(tools=tool_map, cleanup=client.close)
    except Exception as err:
        logger.warning(
            "bridge-planner-agent: failed to load MCP tools — agent will run without them: %s",
            err,
        )
        return McpToolsResult(tools=_make_empty_tools(), cleanup=None)
