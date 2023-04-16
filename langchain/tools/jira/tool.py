from typing import Any, Dict, Optional

from pydantic import Field, root_validator

from langchain.tools.base import BaseTool
from langchain.utilities.jira import JiraAPIWrapper

"""
This tool allows agents to interact with the atlassian-python-api library and operate on a Jira instance.
for more information on the atlassian-python-api library, see https://atlassian-python-api.readthedocs.io/jira.html

To use this tool, you must first set as environment variables:
    JIRA_API_TOKEN
    JIRA_USERNAME
    JIRA_INSTANCE_URL

Below is a sample script that uses the Jira tool:

```python
from langchain.agents import AgentType
from langchain.agents import initialize_agent
from langchain.agents.agent_toolkits.jira.toolkit import JiraToolkit
from langchain.llms import OpenAI
from langchain.utilities.jira import JiraAPIWrapper

llm = OpenAI(temperature=0)
jira = JiraAPIWrapper()
toolkit = JiraToolkit.from_jira_api_wrapper(jira)
agent = initialize_agent(
    toolkit.get_tools(),
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)
```
"""
class JiraAction(BaseTool):
    api_wrapper: JiraAPIWrapper = Field(default_factory=JiraAPIWrapper)
    action_id: str
    name = ""
    description = ""

    def _run(self, instructions: str) -> str:
        """Use the Atlassian Jira API to run an operation."""
        return self.api_wrapper.run(self.action_id, instructions)

    async def _arun(self, _: str) -> str:
        """Use the Atlassian Jira API to run an operation."""
        raise NotImplementedError("JiraAction does not support async")
