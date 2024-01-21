"""
This tool allows agents to interact with the python-gitlab library
and operate on a GitLab repository.

To use this tool, you must first set as environment variables:
    GITLAB_PRIVATE_ACCESS_TOKEN
    GITLAB_REPOSITORY -> format: {owner}/{repo}

"""
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool

from langchain_community.utilities.gitlab import GitLabAPIWrapper


class GitLabActionToolInput(BaseModel):
    instructions: str = Field(
        description="Instruction associated with a action on GitLab"
    )


class GitLabAction(BaseTool):
    """Tool for interacting with the GitLab API."""

    api_wrapper: GitLabAPIWrapper = Field(default_factory=GitLabAPIWrapper)
    mode: str
    name: str = ""
    description: str = ""
    args_schema: Type[BaseModel] = GitLabActionToolInput

    def _run(
        self,
        instructions: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the GitLab API to run an operation."""
        return self.api_wrapper.run(self.mode, instructions)
