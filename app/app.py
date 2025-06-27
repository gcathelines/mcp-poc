import asyncio

from agent import graph
from langgraph.graph import StateGraph


async def loop(graph: StateGraph):
    config = {"configurable": {"thread_id": "1"}}
    print("\n🎯 My Agent")
    print("Commands:")
    print("  quit - Exit the client\n")

    while True:
        try:
            message = input("🧠 You: ").strip()

            if not message:
                continue

            if message == "quit":
                break

            else:
                result = await graph.ainvoke({"messages": [("user", message)]}, config)
                print(f"\n🤖 Assistant: {result['messages'][-1].content}")
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            break


asyncio.run(loop(graph))
