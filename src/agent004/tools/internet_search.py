import os
from typing import Literal, Optional

from langchain_core.tools import tool
from langchain_tavily import TavilySearch


@tool
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> str:
    """Run a web search."""
    tavily = TavilySearch(
        max_results=max_results,
        tavily_api_key=os.environ.get("TAVILY_API_KEY"),
        include_raw_content=include_raw_content,
        topic=topic,
    )
    return tavily.invoke({"query": query})
