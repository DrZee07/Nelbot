"""Chain that carries on a conversation and calls an LLM."""
from typing import Dict, List

from pydantic import ConfigDict, Field, model_validator

from langchain.chains.conversation.prompt import PROMPT
from langchain.chains.llm import LLMChain
from langchain.memory.buffer import ConversationBufferMemory
from langchain.schema import BaseMemory, BasePromptTemplate


class ConversationChain(LLMChain):
    """Chain to have a conversation and load context from memory.

    Example:
        .. code-block:: python

            from langchain import ConversationChain, OpenAI

            conversation = ConversationChain(llm=OpenAI())
    """

    memory: BaseMemory = Field(default_factory=ConversationBufferMemory)
    """Default memory store."""
    prompt: BasePromptTemplate = PROMPT
    """Default conversation prompt to use."""

    input_key: str = "input"  #: :meta private:
    output_key: str = "response"  #: :meta private:
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    @property
    def input_keys(self) -> List[str]:
        """Use this since so some prompt vars come from history."""
        return [self.input_key]

    @model_validator()
    @classmethod
    def validate_prompt_input_variables(cls, values: Dict) -> Dict:
        """Validate that prompt input variables are consistent."""
        memory_keys = values["memory"].memory_variables
        input_key = values["input_key"]
        if input_key in memory_keys:
            raise ValueError(
                f"The input key {input_key} was also found in the memory keys "
                f"({memory_keys}) - please provide keys that don't overlap."
            )
        prompt_variables = values["prompt"].input_variables
        expected_keys = memory_keys + [input_key]
        if set(expected_keys) != set(prompt_variables):
            raise ValueError(
                "Got unexpected prompt input variables. The prompt expects "
                f"{prompt_variables}, but got {memory_keys} as inputs from "
                f"memory, and {input_key} as the normal input key."
            )
        return values
