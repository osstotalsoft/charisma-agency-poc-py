import operator
import os
from typing import Annotated

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

model = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))


# Define tools
@tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    return a / b


tools_by_name = {
    "add": add,
    "multiply": multiply,
    "divide": divide,
}
tools = list(tools_by_name.values())
model_with_tools = model.bind_tools(tools)


class MessagesState(TypedDict):
    messages: Annotated[list, add_messages]
    llm_calls: Annotated[int, operator.add]


def llm_call(state: MessagesState) -> dict:
    response = model_with_tools.invoke(
        [
            SystemMessage(
                content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
            ),
            *state["messages"],
        ]
    )
    return {"messages": [response], "llm_calls": 1}


def tool_node(state: MessagesState) -> dict:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return {"messages": []}

    results: list[ToolMessage] = []
    for tool_call in last_message.tool_calls or []:
        t = tools_by_name[tool_call["name"]]
        observation = t.invoke(tool_call)
        results.append(observation)

    return {"messages": results}


def should_continue(state: MessagesState) -> str:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return END
    if last_message.tool_calls:
        return "tool_node"
    return END


agent = (
    StateGraph(MessagesState)
    .add_node("llm_call", llm_call)
    .add_node("tool_node", tool_node)
    .add_edge(START, "llm_call")
    .add_conditional_edges("llm_call", should_continue, ["tool_node", END])
    .add_edge("tool_node", "llm_call")
    .compile()
)
