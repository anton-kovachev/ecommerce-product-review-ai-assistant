from typing import Any, TypedDict, Annotated
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from models import UserMessageTypeModel, EvaluatorOutput
from langchain_core.messages import BaseMessage


class SidekickState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    todos: Annotated[list[dict[str, Any]], add_messages]
    message_type: UserMessageTypeModel | None
    evaluation_result: EvaluatorOutput | None
