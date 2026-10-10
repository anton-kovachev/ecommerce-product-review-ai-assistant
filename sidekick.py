import os
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from middleware import AsyncToolCallLogger, TolerateToolErrors
from models import EvaluatorOutput, UserMessageTypeModel, FeedbackSentimentOutput
from pydantic import ValidationError
from prompts import (
    PRODUCT_RESEARCHER_PROMPT,
    PRODUCT_REVIEW_EVALUATION_PROMPT,
    USER_MESSAGE_CLASSIFICATOR,
    USER_FEEDBACK_SENTIMENT_ANALYZER,
)
from sidekick_tools import get_all_tools
from state import SidekickState
from enum import Enum

from product_researcher import ProductResearcher
from product_review_evaluator import ProductReviewEvaluator
from message_type_analyzer import MessageTypeAnalyzer
from feedback_sentiment_analyzer import FeedbackSentimentAnalyzer
from guardrails import GuardrailsManager, ModerationResult
import json


class NodeNames(str, Enum):
    START = ("START",)
    END = ("END",)
    MESSAGE_INPUT_MODERATION_ANALYSIS = "message_input_moderation_analysis"
    MESSAGE_INPUT_MODERATED = "message_input_moderated"
    MESSAGE_TYPE_ANALYSIS = "message_type_analysis"
    PROCESS_PRODUCT_QUERY = "process_product_query"
    PROCESS_MODERATED_PRODUCT_QUERY = "process_moderated_product_query"
    PROCESS_FEEDBACK = "process_feedback"
    PROCESS_UNKNOWN = "process_unknown"
    EVALUATE_PRODUCT_REVIEW = "evaluate_product_review"


load_dotenv(override=True)

PROVIDER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.join(HERE, "sandbox")


def get_provider_api_key() -> str:
    if PROVIDER_API_KEY is None:
        raise ValueError("OPENROUTER_API_KEY must be set before creating the model.")
    return PROVIDER_API_KEY


class Sidekick:
    def __init__(self):
        self.sidekick_id = str(uuid.uuid4())
        self.backend = FilesystemBackend(root_dir=SANDBOX, virtual_mode=True)
        self.state: SidekickState = {
            "messages": [],
            "todos": [],
            "message_type": None,
            "evaluation_result": None,
            "moderation_result": None,
        }
        self.memory: InMemorySaver = InMemorySaver()
        self.model: BaseChatModel | ChatOpenAI
        self.guardrails_manager: GuardrailsManager
        self.message_type_analyzer: MessageTypeAnalyzer
        self.product_researcher: ProductResearcher
        self.product_review_evaluator: ProductReviewEvaluator
        self.feedback_sentiment_analyzer: FeedbackSentimentAnalyzer
        self.graph: CompiledStateGraph
        self.todos: list[dict[str, Any]] = []
        self.paused: bool = False
        self.tools: list[Any] = []
        self.sessions = None

    async def setup(self):
        # Setup logic for the Sidekick instance
        self._setup_model()
        await self._setup_tools()
        self.guardrails_manager = GuardrailsManager(self.model)
        self.message_type_analyzer = MessageTypeAnalyzer(self.model)
        self.product_researcher = ProductResearcher(
            self.model, self.tools, self.backend, self.memory
        )
        self.product_review_evaluator = ProductReviewEvaluator(
            self.model, self.backend, self.memory
        )
        self.feedback_sentiment_analyzer = FeedbackSentimentAnalyzer(self.model)

        self.graph = self._build_sidekick_graph()

    def cleanup(self):
        # ...existing code...
        self.paused = False

    def _parse_evaluator_output(self, value: Any) -> EvaluatorOutput | None:
        if value is None:
            return None

        if isinstance(value, EvaluatorOutput):
            return value

        try:
            if isinstance(value, str):
                return EvaluatorOutput.model_validate_json(value)
            return EvaluatorOutput.model_validate(value)
        except ValidationError, TypeError, ValueError:
            return None

    async def _node_moderate_message_input(
        self, state: SidekickState
    ) -> dict[str, Any]:
        print(f"Moderate message input {state["messages"][-1]}")
        validation_result = await self.guardrails_manager.validate_input(
            str(state["messages"][-1].content)
        )
        moderation_result: ModerationResult = validation_result["moderation"]
        if not validation_result["is_valid"] and moderation_result.is_safe:
            moderation_result = ModerationResult(
                is_safe=False,
                reason="; ".join(validation_result["issues"]),
                category="input_validation",
            )
        return {"moderation_result": moderation_result}

    async def _node_define_message_type(self, state: SidekickState) -> dict[str, Any]:
        print(f"Analyze message type {state["messages"][-1]}")

        message_type_query = {
            "messages": [
                HumanMessage(content="Tell me about STIHL MS 212"),
                AIMessage(
                    content=UserMessageTypeModel(
                        category="product_query",
                        content="Tell me about STIHL MS 212",
                        confidence=10,
                    ).model_dump_json()
                ),
                HumanMessage(
                    content="Tell me about the hedge trimmer HS 45 produced by STIHL"
                ),
                AIMessage(
                    content=UserMessageTypeModel(
                        category="product_query",
                        content="Tell me about the hedge trimmer SITHL HS 45",
                        confidence=10,
                    ).model_dump_json()
                ),
                HumanMessage(content="Good job!"),
                AIMessage(
                    content=UserMessageTypeModel(
                        category="product_review_feedback",
                        content="Tell me about the hedge trimmer SITHL HS 45",
                        confidence=8,
                    ).model_dump_json()
                ),
                HumanMessage(state["messages"][-1].content),
            ]
        }
        agent_response = await self.message_type_analyzer.analyze(message_type_query)
        print(f"Agent Response {agent_response["structured_response"]}")
        return {"message_type": agent_response["structured_response"]}

    async def _node_process_moderated_input(
        self, state: SidekickState
    ) -> dict[str, Any]:
        moderation_result: ModerationResult = state.get("moderation_result", None)

        if moderation_result is not None and not moderation_result.is_safe:
            return {
                "messages": [
                    AIMessage(
                        content=f"You query is not safe due to the following reason {moderation_result.reason}"
                    )
                ]
            }
        else:
            return {"messages": [AIMessage(content="Sorry, something went wrong.")]}

    async def _node_process_product_query(self, state: SidekickState) -> dict[str, Any]:
        if self.product_researcher is None:
            raise ValueError(
                "Product researcher must be set up before processing product queries."
            )

        print(f"Process product query input: {state["messages"][-1]}")
        config: RunnableConfig = {
            "configurable": {"reviewer_thread_id": self.sidekick_id}
        }
        response = None

        product_review = state["messages"][-1].additional_kwargs.get("product_review")

        review_rejection_content: str = f"""This is the product review delimited by triple backticks:
    ```{product_review}```
    This is the rejection reason delimited by triple backticks:
    ```{state["messages"][-1].content}```
    Please rewrite the review to match the success criteria requirements specified and taking into consideration the reasons for rejection."""

        print(f"Review rejection content: {review_rejection_content}")
        product_query = (
            state["messages"][-1]
            if product_review is None
            else [
                HumanMessage(
                    content=f"""This is the product review delimited by triple backticks: 
                                    ```{product_review}```
                                  and this is the rejection reason :: ```{state["messages"][-1].content}```
                                  Please rewrite the review to match the success criteria requirments specified and taking into consideration the reasons for rejection."""
                )
            ]
        )
        async for result in self.product_researcher.research(
            {"messages": product_query}, config=config
        ):
            self.todos = result.get("todos", self.todos)

            if "__interrupt__" in result:
                pass

            response = result

        return {
            "messages": (
                response["messages"][-1] if response and "messages" in response else []
            )
        }

    async def _node_process_feedback(self, state: SidekickState) -> dict[str, Any]:
        feedback_message = state["messages"][-1]
        feedback_content = feedback_message.content

        response: dict[str, Any] = (
            await self.feedback_sentiment_analyzer.analyze_sentiment(
                {
                    "messages": [
                        HumanMessage(content="Yes it is a good product review."),
                        AIMessage(
                            content="Thanks for the feedback, is there something other than i be of help."
                        ),
                        HumanMessage(content="This was not what i was looking for."),
                        AIMessage(content="Sorry to hear that"),
                        HumanMessage(content=feedback_content),
                    ]
                }
            )
        )

        structured_response = FeedbackSentimentOutput.model_validate_json(
            str(response["messages"][-1].content)
        )

        return {"messages": [AIMessage(content=structured_response.sentiment)]}

    async def _node_process_evaluate_product_review(
        self,
        state: SidekickState,
    ) -> dict[str, Any]:
        if self.product_review_evaluator is None:
            raise ValueError(
                "Product review evaluator must be set up before processing evaluations."
            )

        product_review = state["messages"][-1].content
        print(f"Evaluating product review: {product_review}")
        config: RunnableConfig = {
            "configurable": {"thread_id": f"{self.sidekick_id}_evaluator"}
        }

        agent_response = await self.product_review_evaluator.evaluate(
            {"messages": HumanMessage(content=product_review)}, config=config
        )

        raw_structured = (
            agent_response.get("structured_response")
            if isinstance(agent_response, dict)
            else None
        )
        evaluation_result = self._parse_evaluator_output(raw_structured)

        if evaluation_result is None and isinstance(agent_response, dict):
            evaluation_result = self._parse_evaluator_output(agent_response)

        if evaluation_result is None:
            return {}

        return {
            "messages": (
                [
                    HumanMessage(
                        content=f"""The product review
                                ```
                                    {product_review}```
                                ```
                                was rejected due to the following reasons ```{evaluation_result.reasoning}``` 
                                Please rewrite the review to match the product success criteria requiremnts specified. 
                                """,
                        additional_kwargs={"product_review": product_review},
                    )
                ]
                if not evaluation_result.verdict
                else []
            ),
            "evaluation_result": evaluation_result,
        }

    def _router_validation_result(
        self, state: SidekickState
    ) -> Literal[NodeNames.PROCESS_PRODUCT_QUERY, NodeNames.END]:
        validation_result = state.get("moderation_result", None)
        if validation_result is None:
            return NodeNames.PROCESS_PRODUCT_QUERY

        return (
            NodeNames.END
            if validation_result.is_safe
            else NodeNames.PROCESS_PRODUCT_QUERY
        )

    def _router_moderation_result(
        self, state: SidekickState
    ) -> Literal[NodeNames.PROCESS_PRODUCT_QUERY, NodeNames.MESSAGE_INPUT_MODERATED]:
        moderation_result = state.get("moderation_result", None)
        if moderation_result is None:
            return NodeNames.PROCESS_PRODUCT_QUERY

        return (
            NodeNames.MESSAGE_INPUT_MODERATED
            if not moderation_result.is_safe
            else NodeNames.PROCESS_PRODUCT_QUERY
        )

    def _router_message_type(
        self,
        state: SidekickState,
    ) -> Literal[
        NodeNames.PROCESS_PRODUCT_QUERY,
        NodeNames.PROCESS_FEEDBACK,
        NodeNames.PROCESS_UNKNOWN,
    ]:
        message_type_model = state.get("message_type")
        message_type = message_type_model.category if message_type_model else "unknown"
        if message_type == "product_query":
            return NodeNames.PROCESS_PRODUCT_QUERY
        elif message_type == "product_review_feedback":
            return NodeNames.PROCESS_FEEDBACK
        else:
            return NodeNames.PROCESS_UNKNOWN

    def _router_evaluation(
        self,
        state: SidekickState,
    ) -> Literal[NodeNames.PROCESS_PRODUCT_QUERY, NodeNames.END]:
        evaluation_result = self._parse_evaluator_output(state.get("evaluation_result"))
        if evaluation_result is None:
            return NodeNames.PROCESS_PRODUCT_QUERY

        return (
            NodeNames.END
            if evaluation_result.verdict
            else NodeNames.PROCESS_PRODUCT_QUERY
        )

    async def arun_turn(
        self,
        message: str,
    ) -> dict[str, Any]:
        config = RunnableConfig(configurable={"thread_id": self.sidekick_id})
        return await self.graph.ainvoke(
            {"messages": [HumanMessage(content=message)]}, config=config
        )

    def _build_sidekick_graph(self) -> CompiledStateGraph:
        if self.message_type_analyzer is None:
            raise ValueError(
                "Message analyzer must be set up before building the state graph."
            )

        sidekick_builder = StateGraph(SidekickState)

        # Nodes
        sidekick_builder.add_node(
            NodeNames.MESSAGE_INPUT_MODERATION_ANALYSIS,
            self._node_moderate_message_input,
        )
        sidekick_builder.add_node(
            NodeNames.MESSAGE_INPUT_MODERATED, self._node_process_moderated_input
        )
        sidekick_builder.add_node(
            NodeNames.MESSAGE_TYPE_ANALYSIS, self._node_define_message_type
        )
        sidekick_builder.add_node(
            NodeNames.PROCESS_PRODUCT_QUERY, self._node_process_product_query
        )
        sidekick_builder.add_node(
            NodeNames.PROCESS_FEEDBACK, self._node_process_feedback
        )
        sidekick_builder.add_node(
            NodeNames.PROCESS_UNKNOWN,
            lambda state: {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "I'm sorry, I didn't understand your message. Could you please clarify or provide more details?",
                    }
                ]
            },
        )
        sidekick_builder.add_node(
            NodeNames.EVALUATE_PRODUCT_REVIEW,
            self._node_process_evaluate_product_review,
        )

        # Edges
        sidekick_builder.add_edge(START, NodeNames.MESSAGE_INPUT_MODERATION_ANALYSIS)
        sidekick_builder.add_conditional_edges(
            NodeNames.MESSAGE_INPUT_MODERATION_ANALYSIS,
            self._router_moderation_result,
            {
                NodeNames.MESSAGE_INPUT_MODERATED: NodeNames.MESSAGE_INPUT_MODERATED,
                NodeNames.PROCESS_PRODUCT_QUERY: NodeNames.MESSAGE_TYPE_ANALYSIS,
            },
        )

        sidekick_builder.add_conditional_edges(
            NodeNames.MESSAGE_TYPE_ANALYSIS, self._router_message_type
        )

        sidekick_builder.add_edge(
            NodeNames.PROCESS_PRODUCT_QUERY, NodeNames.EVALUATE_PRODUCT_REVIEW
        )
        sidekick_builder.add_edge(NodeNames.PROCESS_FEEDBACK, END)
        sidekick_builder.add_edge(NodeNames.PROCESS_UNKNOWN, END)
        sidekick_builder.add_conditional_edges(
            NodeNames.EVALUATE_PRODUCT_REVIEW,
            self._router_evaluation,
            {
                "END": END,
                NodeNames.PROCESS_PRODUCT_QUERY: NodeNames.PROCESS_PRODUCT_QUERY,
            },
        )

        return sidekick_builder.compile(checkpointer=self.memory)

    def _setup_model(self):
        self.model = ChatOpenAI(
            model="openai/gpt-5.4-mini",
            api_key=get_provider_api_key,
            base_url=BASE_URL,
        )

    # Removed old setup methods as they are now handled by agent classes

    async def _setup_tools(self):
        self.tools, self.sessions = await get_all_tools(SANDBOX)
