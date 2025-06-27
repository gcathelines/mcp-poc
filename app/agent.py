import asyncio

from langchain_core.messages import SystemMessage

# from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

client = MultiServerMCPClient(
    {
        "bigquery": {
            "url": "http://localhost:4200/mcp/",
            "transport": "streamable_http",
        },
    }
)


async def main():
    tools = await client.get_tools()

    # Define LLM with bound tools
    # model = os.getenv("OLLAMA_MODEL", "mistral:latest")
    # llm = ChatOllama(model=model)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    llm_with_tools = llm.bind_tools(tools)

    # System message
    sys_msg = SystemMessage(
        content="You are a helpful assistant tasked with analyzing data from bigquery datasets."
    )

    # Node
    def assistant(state: MessagesState) -> MessagesState:
        return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

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
    global graph
    graph = builder.compile()


asyncio.run(main())
