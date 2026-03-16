import asyncio
import os

from deepagents import create_deep_agent

from .system_prompt import get_system_prompt
from .tools.internet_search import internet_search
from .tools.mcp_tools import UserContext, load_mcp_tools


async def _build_agent():
    mcp_result = await load_mcp_tools(
        UserContext(
            tenant_id=os.environ.get("DEV_TENANT_ID"),
            user_passport=os.environ.get("DEV_USER_PASSPORT"),
            authorization=os.environ.get("DEV_AUTHORIZATION"),
            language=os.environ.get("DEV_LANGUAGE"),
        )
    )

    return create_deep_agent(
        model=f"openai:{os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')}",
        tools=[internet_search, *mcp_result.tools.values()],
        system_prompt=get_system_prompt(),
    )


_loop = asyncio.new_event_loop()
agent = _loop.run_until_complete(_build_agent())
_loop.close()
