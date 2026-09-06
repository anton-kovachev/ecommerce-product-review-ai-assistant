from datetime import UTC, datetime
from typing import Any
from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage
from middleware import AsyncToolCallLogger, TolerateToolErrors
from langchain.agents.middleware import PIIMiddleware
from prompts import PRODUCT_RESEARCHER_PROMPT


class ProductResearcher:
    def __init__(self, model, tools, backend, memory):
        self.model = model
        self.tools = tools
        self.backend = backend
        self.memory = memory
        self.agent = self._setup_agent()

    def _setup_agent(self):
        return create_deep_agent(
            model=self.model,
            tools=self.tools,
            backend=self.backend,
            system_prompt=f"{PRODUCT_RESEARCHER_PROMPT}\nToday is {datetime.now(UTC):%A %d %B %Y}.",
            middleware=[
                AsyncToolCallLogger(),
                TolerateToolErrors(),
                PIIMiddleware("email"),
                PIIMiddleware("credit_card", apply_to_tool_results=True),
            ],
            skills=[
                "/skills/product-search",
                "/skills/product-review-success-criteria",
                "/skills/product-review-summary",
            ],
            checkpointer=self.memory,
        )

    async def research(self, query, config=None):
        async for result in self.agent.astream(
            {"messages": query},
            config=config,
            stream_mode="values",
        ):
            yield result
