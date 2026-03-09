from agents import Agent, Runner, TResponseInputItem
from agents.tool import FunctionTool
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from dotenv import load_dotenv
from functools import partial
import os
import asyncio
import json

# Load environment variables
load_dotenv()

# Your Arcade user ID (email) — used to identify the user for authorization
ARCADE_USER_ID = os.getenv("ARCADE_USER_ID")
# Your Arcade API key — used as the Bearer token
ARCADE_API_KEY = os.getenv("ARCADE_API_KEY")
# The Arcade MCP gateway URL
ARCADE_MCP_URL = os.getenv("ARCADE_MCP_URL", "https://api.arcade.dev/mcp/gw_3AXR63VOhhoX8ZHUPtzP3EV4R9D")

# This prompt defines the behavior of the agent.
SYSTEM_PROMPT = (
    "You are a helpful assistant that can assist with Gmail and Slack. "
    "If a tool returns an authorization URL, present it to the user and ask them to complete "
    "authorization in their browser. Once they confirm it's done, automatically retry the "
    "original request without asking again."
)
# This determines which LLM model will be used inside the agent
MODEL = "gpt-4o-mini"


async def invoke_tool(context, args, tool_name: str, client: Client) -> str:
    result = await client.call_tool(tool_name, json.loads(args))
    # FastMCP returns a CallToolResult — extract text from its content items
    parts = [item.text if hasattr(item, "text") else str(item) for item in result.content]
    return "\n".join(parts)


def sanitize_schema(schema: dict) -> dict:
    # OpenAI requires object schemas to have a `properties` field
    if schema.get("type") == "object" and "properties" not in schema:
        schema = {**schema, "properties": {}}
    return schema


async def get_tools(client: Client) -> list[FunctionTool]:
    mcp_tools = await client.list_tools()
    return [
        FunctionTool(
            name=tool.name,
            description=tool.description or "",
            params_json_schema=sanitize_schema(tool.inputSchema),
            on_invoke_tool=partial(invoke_tool, tool_name=tool.name, client=client),
            strict_json_schema=False,
        )
        for tool in mcp_tools
    ]


async def main():
    # Connect to Arcade's MCP gateway via streamable HTTP with header auth
    transport = StreamableHttpTransport(
        url=ARCADE_MCP_URL,
        headers={
            "Authorization": f"Bearer {ARCADE_API_KEY}",
            "Arcade-User-ID": ARCADE_USER_ID,
        },
    )

    async with Client(transport) as client:
        # Fetch tools from the gateway and convert to OpenAI Agents SDK FunctionTools
        tools = await get_tools(client)

        # Create an agent with the fetched tools
        agent = Agent(
            name="Inbox Assistant",
            instructions=SYSTEM_PROMPT,
            model=MODEL,
            tools=tools,
        )

        # Initialize the conversation
        history: list[TResponseInputItem] = []
        # Run the loop
        while True:
            prompt = input("You: ")
            if prompt.lower() == "exit":
                break
            history.append({"role": "user", "content": prompt})
            result = await Runner.run(
                starting_agent=agent,
                input=history,
            )
            history = result.to_input_list()
            print(f"Assistant: {result.final_output}")


# Run the main function as the entry point of the script
if __name__ == "__main__":
    asyncio.run(main())
