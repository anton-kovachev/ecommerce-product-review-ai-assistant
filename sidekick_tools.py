"""Tools for the Sidekick: a mix of MCP servers, ready-made LangChain tools and our own."""

import asyncio
import os
from contextlib import AsyncExitStack

import requests
from requests import Response
from dotenv import load_dotenv
from langchain_community.utilities import GoogleSerperAPIWrapper, WikipediaAPIWrapper
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from db_tools import search_products
from pydantic import BaseModel, Field
from pathlib import Path

load_dotenv(override=True)

LOGS_PATH = (
    Path(__file__).resolve().parent / "sandbox" / "logs.txt"
)  # ensure the workspace exists


@tool
def send_push_notification(text: str) -> str:
    """Send a short push notification to the user's phone."""
    response = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        },
    )
    response.raise_for_status()
    return "Notification sent"


@tool
def log_skill_usage(skill_name: str, usage_details: str) -> str:
    """Log the usage of a skill for analytics and monitoring purposes."""
    # In a real application, you would send this data to a logging service or database.
    print(f"Skill Used: {skill_name}, Details: {usage_details}")
    with open(LOGS_PATH, "a") as log_file:
        log_file.write(f"Skill Used: {skill_name}, Details: {usage_details}\n")
    return "Skill usage logged"


@tool
def request_human_help(instructions: str) -> str:
    """Ask the user to do something in the browser window that you cannot do yourself,
    such as logging in to a site, passing a captcha, or approving two-factor authentication.
    Explain exactly what you need them to do. The run pauses until they have done it."""
    return "The user says it is done. Continue with the task."


def mcp_connections(sandbox: str) -> dict:
    """The MCP servers the Sidekick uses: a headed browser and a sandbox filesystem."""
    return {
        # "playwright": {
        #     "transport": "stdio",
        #     "command": "npx",
        #     "args": ["@playwright/mcp@latest", "--isolated"],
        # },
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", sandbox],
        },
    }


class McpSessions:
    """Holds persistent MCP sessions open so the browser keeps its state between tool calls.

    The stdio transport must be opened and closed from the same asyncio task, so one
    background task owns the sessions: it opens them, waits, and unwinds them when stop()
    is called. Stopping shuts down the servers, and you will see the browser close.
    """

    def __init__(self, connections: dict):
        self.connections = connections
        self.tools = []
        self._ready = asyncio.Event()
        self._stop = asyncio.Event()
        self._task = None

    async def _run(self):
        client = MultiServerMCPClient(self.connections)
        async with AsyncExitStack() as stack:
            for name in self.connections:
                session = await stack.enter_async_context(client.session(name))
                self.tools += await load_mcp_tools(session, server_name=name)
            self._ready.set()
            await self._stop.wait()

    async def start(self) -> list:
        self._task = asyncio.create_task(self._run())
        ready = asyncio.create_task(self._ready.wait())
        await asyncio.wait([ready, self._task], return_when=asyncio.FIRST_COMPLETED)
        ready.cancel()
        if self._task.done():
            self._task.result()  # the servers failed to start; raise the real error
        return self.tools

    def stop(self):
        self._stop.set()


async def get_all_tools(sandbox: str):
    """Return the full tool list (our tools plus the MCP server tools) and the session holder."""
    sessions = McpSessions(mcp_connections(sandbox))
    mcp_tools = await sessions.start()
    our_tools = [
        send_push_notification,
        request_human_help,
        search_products,
        log_skill_usage,
    ]
    return our_tools + mcp_tools, sessions
