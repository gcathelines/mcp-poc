import os

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_core.tools import tool as create_tool

# from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.prebuilt.interrupt import HumanInterrupt, HumanInterruptConfig
from langgraph.types import interrupt


import asyncio


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

    # Define LLM with bound tools
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    llm_with_tools = llm.bind_tools(tools)

    # System message
    sys_msg = SystemMessage(
        content="You are a helpful assistant tasked with analyzing data from bigquery datasets."
    )

    # Node
    async def assistant(state: MessagesState) -> MessagesState:
        # The Gemini API requires content to be non-empty.
        # We add a placeholder to the AIMessage if it has tool_calls but empty content.

        response_message = await llm_with_tools.ainvoke([sys_msg] + state["messages"])
        return {"messages": [response_message]}

    # Build graph
    builder = StateGraph(MessagesState)
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
        # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
        tools_condition,
    )
    builder.add_edge("tools", "assistant")

    return builder


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

        response = interrupt([request])[0]
        if response["type"] == "accept":
            tool_response = await tool.ainvoke(tool_input, config)
        else:
            tool_response = "Tool call was rejected by the user."

        return tool_response

    return call_tool_with_interrupt


graph = asyncio.run(initialize()).compile()

