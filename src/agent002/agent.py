import os

from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent


@tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f"It's always sunny in {city}!"


agent = create_react_agent(
    model=init_chat_model(
        f"openai:{os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')}"
    ),
    tools=[get_weather],
)
