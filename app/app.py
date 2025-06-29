import os

# The CLI app needs a checkpointer, which is disabled in "studio" mode.
# Unset the AGENT_MODE to ensure the graph is compiled with a checkpointer.
if os.getenv("AGENT_MODE") == "studio":
    del os.environ["AGENT_MODE"]


import asyncio

from agent import graph
from langgraph.graph import StateGraph
from langgraph.types import Command


async def loop(graph: StateGraph):
    config = {"configurable": {"thread_id": "1"}}
    print("\n🎯 My Agent")
    print("Commands:")
    print("  quit - Exit the client\n")

    # you can get the name of the node you want to stream from by checking the graph structure
    resume_command_needed = False
    while True:
        try:
            if resume_command_needed:
                print(
                    "⚒️ Please review the tool call and respond with [y/Y] to accept, other response will treated as no."
                )
                review = input("⚒️ You: ").strip()
                type = "reject"
                resume_command_needed = False
                if review.lower() == "y":
                    type = "accept"
                async for chunk in graph.astream(
                    Command(resume=[{"type": type}]), config
                ):
                    print("--- Chunk from resume stream ---")
                    print(chunk)
                    print("\n")

                    if "__interrupt__" in chunk:
                        resume_command_needed = True
                        break
            else:
                message = input("🧠 You: ").strip()

                if not message:
                    continue

                if message == "quit":
                    break

                else:
                    async for chunk in graph.astream(
                        {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": message,
                                }
                            ]
                        },
                        config,
                    ):
                        print("--- Chunk from initial stream ---")
                        print(chunk)
                        print("\n")

                        if "__interrupt__" in chunk:
                            resume_command_needed = True
                            break

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            break


asyncio.run(loop(graph))
