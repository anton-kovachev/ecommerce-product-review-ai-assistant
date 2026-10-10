from pydantic import BaseModel, Field
from typing import Literal


class UserMessageTypeModel(BaseModel):
    category: Literal["product_query", "product_review_feedback", "unknown"] = Field(
        description="The type of the message."
    )
    confidence: int = Field(
        ge=1, le=10, description="The confidence level of the classification (1-10)."
    )
    content: str = Field(description="The content of the message.")


class EvaluatorOutput(BaseModel):
    verdict: bool = Field(description="Feedback on the assistant's response")
    reasoning: str = Field(description="Reasoning behind the verdict")


class FeedbackSentimentOutput(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="The sentiment of the feedback."
    )
    confidence: int = Field(
        ge=1,
        le=10,
        description="The confidence level of the sentiment analysis (1-10).",
    )
    content: str = Field(description="The text content of the feedback.")


class ValidationResult(BaseModel):
    is_valid: bool = Field(description="Indicates if the input passed validation")
    issues: list[str] = Field(description="List of issues found during validation")
