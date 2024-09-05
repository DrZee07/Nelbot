"""Select examples based on length."""

import re
from typing import Callable, Dict, List

from pydantic import BaseModel, field_validator

from langchain_core.example_selectors.base import BaseExampleSelector
from langchain_core.prompts.prompt import PromptTemplate


def _get_length_based(text: str) -> int:
    return len(re.split("\n| ", text))


class LengthBasedExampleSelector(BaseExampleSelector, BaseModel):
    """Select examples based on length."""

    examples: List[dict]
    """A list of the examples that the prompt template expects."""

    example_prompt: PromptTemplate
    """Prompt template used to format the examples."""

    get_text_length: Callable[[str], int] = _get_length_based
    """Function to measure prompt length. Defaults to word count."""

    max_length: int = 2048
    """Max length for the prompt, beyond which examples are cut."""

    example_text_lengths: List[int] = []  #: :meta private:
    """Length of each example."""

    def add_example(self, example: Dict[str, str]) -> None:
        """Add new example to list.

        Args:
            example: A dictionary with keys as input variables
                and values as their values.
        """
        self.examples.append(example)
        string_example = self.example_prompt.format(**example)
        self.example_text_lengths.append(self.get_text_length(string_example))

    async def aadd_example(self, example: Dict[str, str]) -> None:
        """Async add new example to list.

        Args:
            example: A dictionary with keys as input variables
                and values as their values.
        """

        self.add_example(example)

    @field_validator("example_text_lengths")
    def calculate_example_text_lengths(cls, v: List[int], values: Dict) -> List[int]:
        """Calculate text lengths if they don't exist."""
        # Check if text lengths were passed in
        if v:
            return v
        # If they were not, calculate them
        example_prompt = values["example_prompt"]
        get_text_length = values["get_text_length"]
        string_examples = [example_prompt.format(**eg) for eg in values["examples"]]
        return [get_text_length(eg) for eg in string_examples]

    def select_examples(self, input_variables: Dict[str, str]) -> List[dict]:
        """Select which examples to use based on the input lengths.

        Args:
            input_variables: A dictionary with keys as input variables
               and values as their values.

        Returns:
            A list of examples to include in the prompt.
        """
        inputs = " ".join(input_variables.values())
        remaining_length = self.max_length - self.get_text_length(inputs)
        i = 0
        examples = []
        while remaining_length > 0 and i < len(self.examples):
            new_length = remaining_length - self.example_text_lengths[i]
            if new_length < 0:
                break
            else:
                examples.append(self.examples[i])
                remaining_length = new_length
            i += 1
        return examples

    async def aselect_examples(self, input_variables: Dict[str, str]) -> List[dict]:
        """Async select which examples to use based on the input lengths.

        Args:
            input_variables: A dictionary with keys as input variables
               and values as their values.

        Returns:
            A list of examples to include in the prompt.
        """
        return self.select_examples(input_variables)
