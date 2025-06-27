import asyncio
import os

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage

# from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, Graph, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


async def initialize() -> Graph:
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

    # Compile graph
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    return graph


graph = asyncio.run(initialize())
