from typing import Any
from langchain.agents import create_agent
from prompts import USER_MESSAGE_CLASSIFICATOR
from models import UserMessageTypeModel


class MessageTypeAnalyzer:
    def __init__(self, model):
        self.model = model
        self.agent = self._setup_agent()

    def _setup_agent(self):
        return create_agent(
            name="Message Type Analyzer",
            model=self.model,
            system_prompt=USER_MESSAGE_CLASSIFICATOR,
            response_format=UserMessageTypeModel,
        )

    async def analyze(self, query):
        return await self.agent.ainvoke(query)
