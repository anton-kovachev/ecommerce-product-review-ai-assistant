from typing import Any
from langchain.agents import create_agent
from prompts import USER_FEEDBACK_SENTIMENT_ANALYZER
from models import FeedbackSentimentOutput


class FeedbackSentimentAnalyzer:
    def __init__(self, model):
        self.model = model
        self.agent = self._setup_agent()

    def _setup_agent(self):
        return create_agent(
            name="Feedback Sentiment Analyzer",
            model=self.model,
            system_prompt=USER_FEEDBACK_SENTIMENT_ANALYZER,
            response_format=FeedbackSentimentOutput,
        )

    async def analyze_sentiment(self, query):
        return await self.agent.ainvoke(query)
