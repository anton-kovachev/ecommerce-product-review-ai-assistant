from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from models import EvaluatorOutput, UserMessageTypeModel, ValidationResult


class SidekickState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    todos: Annotated[list[dict[str, Any]], add_messages]
    message_type: UserMessageTypeModel | None
    evaluation_result: EvaluatorOutput | None
    validation_result: ValidationResult | None
