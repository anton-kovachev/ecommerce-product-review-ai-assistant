from datetime import UTC, datetime
from typing import Any
from deepagents import create_deep_agent
from middleware import AsyncToolCallLogger, TolerateToolErrors
from prompts import PRODUCT_REVIEW_EVALUATION_PROMPT
from models import EvaluatorOutput


class ProductReviewEvaluator:
    def __init__(self, model, backend, memory):
        self.model = model
        self.backend = backend
        self.memory = memory
        self.agent = self._setup_agent()

    def _setup_agent(self):
        return create_deep_agent(
            model=self.model,
            backend=self.backend,
            system_prompt=f"{PRODUCT_REVIEW_EVALUATION_PROMPT}\nToday is {datetime.now(UTC):%A %d %B %Y}.",
            middleware=[
                AsyncToolCallLogger(),
                TolerateToolErrors(),
            ],
            skills=["/skills/product-review-success-criteria"],
            checkpointer=self.memory,
            response_format=EvaluatorOutput,
        )

    async def evaluate(self, query, config=None):
        return await self.agent.ainvoke(query, config=config)
