"""A fake callback handler for testing purposes."""
from typing import Any, Dict, List

from pydantic import BaseModel

from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult


class FakeCallbackHandler(BaseModel, BaseCallbackHandler):
    """Fake callback handler for testing."""

    starts: int = 0
    ends: int = 0
    errors: int = 0
    text: int = 0
    ignore_llm_: bool = False
    ignore_chain_: bool = False
    ignore_agent_: bool = False

    @property
    def ignore_llm(self) -> bool:
        """Whether to ignore LLM callbacks."""
        return self.ignore_llm_

    @property
    def ignore_chain(self) -> bool:
        """Whether to ignore chain callbacks."""
        return self.ignore_chain_

    @property
    def ignore_agent(self) -> bool:
        """Whether to ignore agent callbacks."""
        return self.ignore_agent_

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.starts += 1

    def on_llm_end(
        self,
        response: LLMResult,
    ) -> None:
        """Run when LLM ends running."""
        self.ends += 1

    def on_llm_error(self, error: Exception) -> None:
        """Run when LLM errors."""
        self.errors += 1

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""
        self.starts += 1

    def on_chain_end(self, outputs: Dict[str, Any]) -> None:
        """Run when chain ends running."""
        self.ends += 1

    def on_chain_error(self, error: Exception) -> None:
        """Run when chain errors."""
        self.errors += 1

    def on_tool_start(
        self, serialized: Dict[str, Any], action: AgentAction, **kwargs: Any
    ) -> None:
        """Run when tool starts running."""
        self.starts += 1

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running."""
        self.ends += 1

    def on_tool_error(self, error: Exception) -> None:
        """Run when tool errors."""
        self.errors += 1

    def on_text(self, text: str, **kwargs: Any) -> None:
        """Run when agent is ending."""
        self.text += 1

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run when agent ends running."""
        self.ends += 1
