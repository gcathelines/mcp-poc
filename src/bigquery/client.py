import asyncio
from datetime import timedelta
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def call_tool(
    session: ClientSession, tool_name: str, arguments: dict[str, Any] | None = None
):
    """Call a specific tool."""

    try:
        result = await session.call_tool(tool_name, arguments or {})
        print(f"\n🔧 Tool '{tool_name}' result:")
        if hasattr(result, "content"):
            for content in result.content:
                if content.type == "text":
                    print(content.text)
                else:
                    print(content)
        else:
            print(result)
    except Exception as e:
        print(f"❌ Failed to call tool '{tool_name}': {e}")


async def list_tools(session: ClientSession):
    """List available tools from the server."""

    try:
        result = await session.list_tools()
        if hasattr(result, "tools") and result.tools:
            print("\n📋 Available tools:")
            for i, tool in enumerate(result.tools, 1):
                print(f"{i}. {tool.name}")
                if tool.description:
                    print(f"   Description: {tool.description}")
                print()
        else:
            print("No tools available")
    except Exception as e:
        print(f"❌ Failed to list tools: {e}")


async def main():
    # Connect to a streamable HTTP server
    async with streamablehttp_client(
        url="http://localhost:4200/mcp",  # Replace with your server URL
        timeout=timedelta(seconds=5),  # Optional timeout for the connection
    ) as (
        read_stream,
        write_stream,
        _,
    ):
        # Create a session using the client streams
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()
            # Call a tool

            print("\n🎯 Interactive MCP Client")
            print("Commands:")
            print("  list - List available tools")
            print("  call <tool_name> [args] - Call a tool")
            print("  quit - Exit the client")
            print()

            while True:
                try:
                    command = input("mcp> ").strip()

                    if not command:
                        continue

                    if command == "quit":
                        break

                    elif command == "list":
                        await list_tools(session)

                    elif command.startswith("call "):
                        parts = command.split(maxsplit=2)
                        tool_name = parts[1] if len(parts) > 1 else ""

                        if not tool_name:
                            print("❌ Please specify a tool name")
                            continue

                        # Parse arguments (simple JSON-like format)
                        arguments = {}
                        if len(parts) > 2:
                            import json

                            try:
                                arguments = json.loads(parts[2])
                            except json.JSONDecodeError:
                                print("❌ Invalid arguments format (expected JSON)")
                                continue

                        await call_tool(session, tool_name, arguments)

                    else:
                        print(
                            "❌ Unknown command. Try 'list', 'call <tool_name>', or 'quit'"
                        )

                except KeyboardInterrupt:
                    print("\n\n👋 Goodbye!")
                    break
                except EOFError:
                    break


def cli():
    """CLI entry point for uv script."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
