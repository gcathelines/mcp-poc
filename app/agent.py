import asyncio
import os
from typing import Any, Literal, Union

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_core.tools import tool as create_tool

# from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.prebuilt.interrupt import HumanInterrupt, HumanInterruptConfig
from langgraph.types import interrupt


class State(MessagesState):
    summary: str
    need_summarization: bool = False


async def initialize() -> StateGraph:
    env = load_dotenv()
    if not env:
        raise RuntimeError("Failed to load environment variables from .env file.")

    client = MultiServerMCPClient(
        {
            "bigquery": {
                "url": "http://localhost:4200/mcp/",
                "transport": "streamable_http",
            },
        }
    )
    tools = await client.get_tools()
    # generate tool calls with human in the loop
    tools = [
        add_human_in_the_loop(
            tool,
            interrupt_config=HumanInterruptConfig(
                description="Please review the tool call",
                action_request_schema=tool.args_schema,
            ),
        )
        for tool in tools
    ]

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    llm_with_tools = llm.bind_tools(tools)

    sys_msg = SystemMessage(
        # content="You are a helpful assistant tasked with analyzing data from bigquery datasets."
        content="You are a helpful assistant."
    )

    async def assistant(state: State) -> State:
        messages = [sys_msg]
        summary = state.get("summary", "")
        if summary:
            system_message = f"Summary of conversation earlier: {summary}"
            messages = messages + [SystemMessage(content=system_message)]
        response_message = await llm_with_tools.ainvoke(messages + state["messages"])
        return {"messages": [response_message]}

    def summarize_conversation(state: State):
        # First, we get any existing summary
        summary = state.get("summary", "")

        # Create our summarization prompt
        if summary:
            # A summary already exists
            summary_message = (
                f"This is summary of the conversation to date: {summary}\n\n"
                "Extend the summary by taking into account the new messages above:"
            )

        else:
            summary_message = "Create a summary of the conversation above:"

        # Add prompt to our history
        messages = state["messages"] + [HumanMessage(content=summary_message)]
        response = llm.invoke(messages)

        # Delete all but the 2 most recent messages
        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
        return State(
            summary=response.content,
            messages=delete_messages,
            need_summarization=False,
        )

    # Build graph
    builder = StateGraph(State)
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("summarize", summarize_conversation)
    builder.add_edge("summarize", END)
    builder.add_conditional_edges(
        "assistant",
        # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
        # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
        tools_condition,
    )
    builder.add_edge("tools", "assistant")

    # builder.add_edge(START, "assistant")
    builder.add_conditional_edges(START, summarize_condition)

    return builder


def summarize_condition(
    state: Union[list[Any], dict[str, Any], Any],
) -> Literal["summarize", "assistant"]:
    if state.get("need_summarization", False):
        # If the state has a summary, we want to summarize the conversation
        return "summarize"
    return "assistant"


def add_human_in_the_loop(
    tool: BaseTool, *, interrupt_config: HumanInterruptConfig = None
) -> BaseTool:
    @create_tool(
        tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
    )
    async def call_tool_with_interrupt(
        config: RunnableConfig,
        **tool_input,
    ):
        request: HumanInterrupt = {
            "action_request": {
                "action": tool.name,
                "args": tool_input,
            },
            "config": interrupt_config,
            "description": "Please review the tool call",
        }

        response = interrupt([request])
        if not isinstance(response, str):
            response = next(iter(response.values()))
        if response == "accept":
            tool_response = await tool.ainvoke(tool_input, config)
        else:
            tool_response = "Tool call was rejected by the user."

        return tool_response

    return call_tool_with_interrupt


graph = asyncio.run(initialize()).compile()
