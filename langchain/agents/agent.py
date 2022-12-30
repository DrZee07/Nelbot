"""Chain that takes in an input and produces an action and action input."""
from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, root_validator

from langchain.agents.tools import Tool
from langchain.callbacks.base import BaseCallbackManager
from langchain.chains.base import Chain
from langchain.chains.llm import LLMChain
from langchain.input import get_color_mapping
from langchain.llms.base import BaseLLM
from langchain.prompts.base import BasePromptTemplate
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain.schema import AGENT_FINISH_OBSERVATION, AgentAction, AgentFinish

logger = logging.getLogger()


class Agent(BaseModel):
    """Class responsible for calling the language model and deciding the action.

    This is driven by an LLMChain. The prompt in the LLMChain MUST include
    a variable called "agent_scratchpad" where the agent can put its
    intermediary work.
    """

    llm_chain: LLMChain
    return_values: List[str] = ["output"]

    @abstractmethod
    def _extract_tool_and_input(self, text: str) -> Optional[Tuple[str, str]]:
        """Extract tool and tool input from llm output."""

    def _fix_text(self, text: str) -> str:
        """Fix the text."""
        raise ValueError("fix_text not implemented for this agent.")

    @property
    def _stop(self) -> List[str]:
        return [f"\n{self.observation_prefix}"]

    def plan(
        self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> AgentAction:
        """Given input, decided what to do.

        Args:
            intermediate_steps: Steps the LLM has taken to date,
                along with observations
            **kwargs: User inputs.

        Returns:
            Action specifying what tool to use.
        """
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\n{self.observation_prefix}{observation}\n{self.llm_prefix}"
        new_inputs = {"agent_scratchpad": thoughts, "stop": self._stop}
        full_inputs = {**kwargs, **new_inputs}
        full_output = self.llm_chain.predict(**full_inputs)
        parsed_output = self._extract_tool_and_input(full_output)
        while parsed_output is None:
            full_output = self._fix_text(full_output)
            full_inputs["agent_scratchpad"] += full_output
            output = self.llm_chain.predict(**full_inputs)
            full_output += output
            parsed_output = self._extract_tool_and_input(full_output)
        tool, tool_input = parsed_output
        if tool == self.finish_tool_name:
            return AgentFinish(tool, tool_input, full_output, {"output": tool_input})
        return AgentAction(tool, tool_input, full_output)

    def prepare_for_new_call(self) -> None:
        """Prepare the agent for new call, if needed."""
        pass

    @property
    def finish_tool_name(self) -> str:
        """Name of the tool to use to finish the chain."""
        return "Final Answer"

    @property
    def input_keys(self) -> List[str]:
        """Return the input keys.

        :meta private:
        """
        return list(set(self.llm_chain.input_keys) - {"agent_scratchpad"})

    @root_validator()
    def validate_prompt(cls, values: Dict) -> Dict:
        """Validate that prompt matches format."""
        prompt = values["llm_chain"].prompt
        if "agent_scratchpad" not in prompt.input_variables:
            logger.warning(
                "`agent_scratchpad` should be a variable in prompt.input_variables."
                " Did not find it, so adding it at the end."
            )
            prompt.input_variables.append("agent_scratchpad")
            if isinstance(prompt, PromptTemplate):
                prompt.template += "\n{agent_scratchpad}"
            elif isinstance(prompt, FewShotPromptTemplate):
                prompt.suffix += "\n{agent_scratchpad}"
            else:
                raise ValueError(f"Got unexpected prompt type {type(prompt)}")
        return values

    @property
    @abstractmethod
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""

    @property
    @abstractmethod
    def llm_prefix(self) -> str:
        """Prefix to append the LLM call with."""

    @classmethod
    @abstractmethod
    def create_prompt(cls, tools: List[Tool]) -> BasePromptTemplate:
        """Create a prompt for this class."""

    @classmethod
    def _validate_tools(cls, tools: List[Tool]) -> None:
        """Validate that appropriate tools are passed in."""
        pass

    @classmethod
    def from_llm_and_tools(
        cls,
        llm: BaseLLM,
        tools: List[Tool],
        callback_manager: Optional[BaseCallbackManager] = None,
    ) -> Agent:
        """Construct an agent from an LLM and tools."""
        cls._validate_tools(tools)
        llm_chain = LLMChain(
            llm=llm, prompt=cls.create_prompt(tools), callback_manager=callback_manager
        )
        return cls(llm_chain=llm_chain)

    def return_stopped_response(self) -> dict:
        """Return response when agent has been stopped due to max iterations."""
        return {k: "Agent stopped due to max iterations." for k in self.return_values}


class AgentExecutor(Chain, BaseModel):
    """Consists of an agent using tools."""

    agent: Agent
    tools: List[Tool]
    return_intermediate_steps: bool = False
    max_iterations: Optional[int] = None

    @classmethod
    def from_agent_and_tools(
        cls,
        agent: Agent,
        tools: List[Tool],
        callback_manager: Optional[BaseCallbackManager] = None,
        **kwargs: Any,
    ) -> AgentExecutor:
        """Create from agent and tools."""
        return cls(
            agent=agent, tools=tools, callback_manager=callback_manager, **kwargs
        )

    @property
    def input_keys(self) -> List[str]:
        """Return the input keys.

        :meta private:
        """
        return self.agent.input_keys

    @property
    def output_keys(self) -> List[str]:
        """Return the singular output key.

        :meta private:
        """
        if self.return_intermediate_steps:
            return self.agent.return_values + ["intermediate_steps"]
        else:
            return self.agent.return_values

    def _should_continue(self, iterations: int) -> bool:
        if self.max_iterations is None:
            return True
        else:
            return iterations < self.max_iterations

    def _call(self, inputs: Dict[str, str]) -> Dict[str, Any]:
        """Run text through and get agent response."""
        # Do any preparation necessary when receiving a new input.
        self.agent.prepare_for_new_call()
        # Construct a mapping of tool name to tool for easy lookup
        name_to_tool_map = {tool.name: tool.func for tool in self.tools}
        # We construct a mapping from each tool to a color, used for logging.
        color_mapping = get_color_mapping(
            [tool.name for tool in self.tools], excluded_colors=["green"]
        )
        intermediate_steps: List[Tuple[AgentAction, str]] = []
        # Let's start tracking the iterations the agent has gone through
        iterations = 0
        # We now enter the agent loop (until it returns something).
        while self._should_continue(iterations):
            # Call the LLM to see what to do.
            output = self.agent.plan(intermediate_steps, **inputs)
            # If the tool chosen is the finishing tool, then we end and return.
            if isinstance(output, AgentFinish):
                if self.verbose:
                    self._get_callback_manager().on_tool_start(
                        {"name": "Finish"}, output, color="green"
                    )
                    self._get_callback_manager().on_tool_end(AGENT_FINISH_OBSERVATION)
                final_output = output.return_values
                if self.return_intermediate_steps:
                    final_output["intermediate_steps"] = intermediate_steps
                return final_output

            # And then we lookup the tool
            if output.tool in name_to_tool_map:
                chain = name_to_tool_map[output.tool]
                if self.verbose:
                    self._get_callback_manager().on_tool_start(
                        {"name": str(chain)[:60] + "..."}, output, color="green"
                    )
                # We then call the tool on the tool input to get an observation
                observation = chain(output.tool_input)
                color = color_mapping[output.tool]
            else:
                if self.verbose:
                    self._get_callback_manager().on_tool_start(
                        {"name": "N/A"}, output, color="green"
                    )
                observation = f"{output.tool} is not a valid tool, try another one."
                color = None
            if self.verbose:
                self._get_callback_manager().on_tool_end(
                    observation,
                    color=color,
                    observation_prefix=self.agent.observation_prefix,
                    llm_prefix=self.agent.llm_prefix,
                )
            intermediate_steps.append((output, observation))
            iterations += 1
        final_output = self.agent.return_stopped_response()
        if self.return_intermediate_steps:
            final_output["intermediate_steps"] = intermediate_steps
        return final_output
