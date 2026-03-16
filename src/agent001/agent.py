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
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


@tool
def power(a: float, b: float) -> float:
    """Compute a raised to the power b."""
    return a**b


@tool
def modulo(a: float, b: float) -> float:
    """Compute a modulo b."""
    if b == 0:
        raise ZeroDivisionError("modulo by zero")
    return a % b


tools_by_name = {
    "add": add,
    "subtract": subtract,
    "multiply": multiply,
    "divide": divide,
    "power": power,
    "modulo": modulo,
}
tools = list(tools_by_name.values())
model_with_tools = model.bind_tools(tools)


class MessagesState(TypedDict):
    messages: Annotated[list, add_messages]
    llm_calls: Annotated[int, operator.add]


SYSTEM_PROMPT = (
    "You are an arithmetic assistant. Solve the user's math problem exactly.\n"
    "Rules:\n"
    "- Use the provided tools for arithmetic operations (add, subtract, multiply, divide, power, modulo).\n"
    "- Follow order of operations and show your work via tool calls when helpful.\n"
    "- If the user asks for a final value, return ONLY the numeric answer (no units, no extra text).\n"
    "- Handle edge cases: if division/modulo by zero would occur, respond with 'ERROR'."
)


def llm_call(state: MessagesState) -> dict:
    response = model_with_tools.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
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
        name = tool_call.get("name")
        t = tools_by_name.get(name)
        if t is None:
            results.append(
                ToolMessage(
                    content=f"ERROR: unknown tool '{name}'",
                    tool_call_id=tool_call.get("id", ""),
                )
            )
            continue
        try:
            observation = t.invoke(tool_call)
        except ZeroDivisionError:
            results.append(
                ToolMessage(
                    content="ERROR",
                    tool_call_id=tool_call.get("id", ""),
                )
            )
        except Exception as e:
            results.append(
                ToolMessage(
                    content=f"ERROR: {type(e).__name__}",
                    tool_call_id=tool_call.get("id", ""),
                )
            )
        else:
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
