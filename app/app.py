import asyncio
import json
import os

from agent import initialize
from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import Runnable
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from psycopg import AsyncConnection


async def loop(graph: Runnable):
    db_conn = await init_db_conn()

    config = {"configurable": {"thread_id": "2"}}
    print("\n🎯 My Agent")
    print("Commands:")
    print("\t/quit - Exit the client")
    print("\t/list - List checkpoints")
    print("\t/new <id>- Create new checkpoint")
    print("\t/resume <id> - Resume checkpoint for given id")
    print("\t/summarize - Summarize the conversation")

    # you can get the name of the node you want to stream from by checking the graph structure
    resume_command_needed = False
    while True:
        try:
            if resume_command_needed:
                review = input("🔧 Use [y/Y] to accept: ").strip()
                type = "reject"
                resume_command_needed = False
                if review.lower() == "y":
                    type = "accept"
                async for stream_mode, chunk in graph.astream(
                    Command(resume=[{"type": type}]),
                    config,
                    stream_mode=["updates", "messages"],
                ):
                    resume_command_needed = process_chunk(stream_mode, chunk)
                    if resume_command_needed:
                        break
            else:
                message = input("🧠 You: ").strip()

                if not message:
                    continue

                if message.startswith("/"):
                    if message == "/quit":
                        print("\n👋 Goodbye!")
                        break
                    elif message == "/list":
                        print("Available checkpoints:")
                        for cpt in await list_checkpoint(db_conn):
                            print(cpt[0])
                    elif message.startswith("/resume "):
                        id = message.split(" ")[1]
                        if not id:
                            print("Please provide a checkpoint ID to resume.")
                            continue
                        threads = await get_checkpoint(db_conn, id)
                        if not threads:
                            print(f"No checkpoint found with ID: {id}")
                            continue
                        else:
                            print(f"Resuming checkpoint with ID: {id}")
                            config = {"configurable": {"thread_id": str(id)}}
                    elif message.startswith("/new "):
                        id = message.split(" ")[1]
                        if not id:
                            print("Please provide a checkpoint ID to create.")
                            continue
                        threads = await get_checkpoint(db_conn, id)
                        if threads:
                            print(f"Checkpoint with ID: {id} already exists.")
                            continue
                        else:
                            print(f"Creating checkpoint with ID: {id}")
                            config = {"configurable": {"thread_id": str(id)}}
                    elif message.startswith("/summarize "):
                        print("Summarizing the conversation...")
                        async for stream_mode, chunk in graph.astream(
                            {"need_summarization": True},
                            config,
                            stream_mode=["updates", "messages"],
                        ):
                            resume_command_needed = process_chunk(stream_mode, chunk)
                            if resume_command_needed:
                                break
                        continue
                else:
                    async for stream_mode, chunk in graph.astream(
                        {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": message,
                                }
                            ]
                        },
                        config,
                        stream_mode=["updates", "messages"],
                    ):
                        resume_command_needed = process_chunk(stream_mode, chunk)
                        if resume_command_needed:
                            break

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            break


async def list_checkpoint(db_conn: AsyncConnection):
    threads = await db_conn.execute("select distinct(thread_id) from checkpoints;")
    return await threads.fetchall()


async def get_checkpoint(db_conn: AsyncConnection, thread_id: str):
    threads = await db_conn.execute(
        "select * from checkpoints where thread_id = %s limit 1;", (thread_id,)
    )
    return await threads.fetchone()


def process_chunk(stream_mode: str, chunk: dict) -> bool:
    if stream_mode == "messages":
        message: AIMessageChunk = chunk[0]
        if message.content:
            if getattr(message, "tool_call_id", None):
                print(f"🔧 Tool call {message.tool_call_id} result:")
                print(f"\t{json.loads(message.content)}")
        return False
    elif stream_mode == "updates":
        if chunk.get("__interrupt__", {}):
            data = chunk["__interrupt__"][-1].value[-1]
            print("🔧 Assistant want to do a tool call with these details:")
            print(
                f"\tTool Name: {data['action_request']['action']}\n\tArgs: {data['action_request']['args']}"
            )
            return True
        if chunk.get("assistant", {}):
            messages = chunk["assistant"]["messages"]
            if messages[0].content:
                print(f"💬 Assistant: {messages[0].content}")
            return False

    return False


async def init_db_conn() -> AsyncConnection:
    return await AsyncConnection.connect(
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )


async def main():
    builder = await initialize()

    graph = builder.compile()
    if os.getenv("AGENT_MODE") == "studio":
        return graph
    else:
        async with AsyncPostgresSaver.from_conn_string(
            "postgresql://postgres:postgres@localhost:5432/postgres"
        ) as checkpointer:
            await checkpointer.setup()
            graph = builder.compile(checkpointer=checkpointer)
            await loop(graph)


if __name__ == "__main__":
    asyncio.run(main())
