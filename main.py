from agents import Agent, Runner, TResponseInputItem
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from dotenv import load_dotenv
import os
import asyncio

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


async def main():
    # Connect to Arcade's MCP gateway via streamable HTTP with header auth
    mcp_server = MCPServerStreamableHttp(
        params=MCPServerStreamableHttpParams(
            url=ARCADE_MCP_URL,
            headers={
                "Authorization": f"Bearer {ARCADE_API_KEY}",
                "Arcade-User-ID": ARCADE_USER_ID,
            },
            timeout=30,
            sse_read_timeout=300,
        ),
        client_session_timeout_seconds=30,
    )

    async with mcp_server:
        # Create an agent — tools are discovered automatically from the MCP gateway
        agent = Agent(
            name="Inbox Assistant",
            instructions=SYSTEM_PROMPT,
            model=MODEL,
            mcp_servers=[mcp_server],
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
