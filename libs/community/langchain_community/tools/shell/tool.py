import sys
import logging
import platform
import warnings
from typing import Any, List, Optional, Type, Union

from langchain_core.callbacks import (
    CallbackManagerForToolRun,
)
from langchain_core.pydantic_v1 import BaseModel, Field, root_validator
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class ShellInput(BaseModel):
    """Commands for the Bash Shell tool."""

    commands: Union[str, List[str]] = Field(
        ...,
        description="List of shell commands to run. Deserialized using json.loads",
    )
    """List of shell commands to run."""

    @root_validator
    def _validate_commands(cls, values: dict) -> dict:
        """Validate commands."""
        # TODO: Add real validators
        commands = values.get("commands")
        if not isinstance(commands, list):
            values["commands"] = [commands]
        # Warn that the bash tool is not safe
        warnings.warn(
            "The shell tool has no safeguards by default. Use at your own risk."
        )
        return values


def _get_default_bash_process() -> Any:
    """Get default bash process."""
    try:
        from langchain_experimental.llm_bash.bash import BashProcess
    except ImportError:
        raise ImportError(
            "BashProcess has been moved to langchain experimental."
            "To use this tool, install langchain-experimental "
            "with `pip install langchain-experimental`."
        )
    return BashProcess(return_err_output=True)


def _get_platform() -> str:
    """Get platform."""
    system = platform.system()
    if system == "Darwin":
        return "MacOS"
    return system


class ShellTool(BaseTool):
    """Tool to run shell commands."""

    process: Any = Field(default_factory=_get_default_bash_process)
    """Bash process to run commands."""

    name: str = "terminal"
    """Name of tool."""

    description: str = f"Run shell commands on this {_get_platform()} machine."
    """Description of tool."""

    args_schema: Type[BaseModel] = ShellInput
    """Schema for input arguments."""

    ask_human_input: bool = False
    """
    If True, prompts the user for confirmation (y/n) before executing 
    a command generated by the language model in the bash shell.
    """

    def _run(
        self,
        commands: Union[str, List[str]],
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Run commands and return final output."""

        logger.info(f"Executing command:\n {commands}")
        
        try:
            if not self.ask_human_input:
                return self.process.run(commands)
            else:
                user_input = input("Proceed with command execution? (y/n): ").lower()
                if user_input == "y":
                    return self.process.run(commands)
                else:
                    logger.info("User aborted command execution.")
                    return None
                
        except Exception as e:
            logger.error(f"Error during command execution: {e}")