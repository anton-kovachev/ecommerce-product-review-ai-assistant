import json
import anyio
from pathlib import Path
from langchain.agents.middleware import wrap_tool_call
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

TOOL_CALL_LOGS_PATH = Path(__file__).parent / "sandbox/tool_calls.txt"


@wrap_tool_call
def log_tool_call_middleware(request, handler):
    tool_name = request.tool_call["name"]

    if tool_name == "search_products":
        # Log the tool call details
        print(f"Tool Call: {tool_name}")
        print(f"Input: {request.tool_call}")
        with open(TOOL_CALL_LOGS_PATH, "a") as log_file:
            log_file.write(
                f"Tool Call: {tool_name}\n Input: {repr(request.tool_call)}\n"
            )
    return handler(request)


class AsyncToolCallLogger(AgentMiddleware):
    async def awrap_tool_call(self, request, handler):
        tool_name = request.tool_call["name"]

        # if tool_name == "search_products":
        print(f"Tool Call: {tool_name}")
        print(f"Input: {request.tool_call}")
        async with await anyio.open_file(TOOL_CALL_LOGS_PATH, "a") as log_file:
            await log_file.write(
                f"Tool Call: {tool_name}\n Input: {repr(request.tool_call)}\n"
            )
        return await handler(request)


class TolerateToolErrors(AgentMiddleware):
    """Hand tool failures back to the model as a message so it can recover, rather than
    crashing the run. Tools that touch the outside world, like a browser, fail now and then.
    """

    @staticmethod
    def _stringify_tool_content(content) -> str:
        if isinstance(content, str):
            return content
        if content is None:
            return ""
        try:
            if isinstance(content, (dict, list, tuple)):
                return json.dumps(content, ensure_ascii=False)
            return str(content)
        except (TypeError, ValueError):
            return repr(content)

    def wrap_tool_call(self, request, handler):
        try:
            response = handler(request)
            content = getattr(response, "content", None)
            if content is not None and not isinstance(content, str):
                return ToolMessage(
                    content=self._stringify_tool_content(content),
                    tool_call_id=getattr(
                        response, "tool_call_id", request.tool_call["id"]
                    ),
                )
            return response
        except Exception as error:
            return ToolMessage(
                content=f"That tool call failed: {error}. Try another approach.",
                tool_call_id=request.tool_call["id"],
            )

    async def awrap_tool_call(self, request, handler):
        try:
            response = await handler(request)
            content = getattr(response, "content", None)
            if content is not None and not isinstance(content, str):
                return ToolMessage(
                    content=self._stringify_tool_content(content),
                    tool_call_id=getattr(
                        response, "tool_call_id", request.tool_call["id"]
                    ),
                )
            return response
        except Exception as error:
            return ToolMessage(
                content=f"That tool call failed: {error}. Try another approach.",
                tool_call_id=request.tool_call["id"],
            )
