from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import root_validator
from langchain_core.tools import BaseTool
from langchain_core.utils import get_from_dict_or_env

logger = logging.getLogger(__name__)


class AzureContentSafetyTextTool(BaseTool):
    """
    A tool that interacts with the Azure AI Content Safety API.

    This tool queries the Azure AI Content Safety API to analyze text for harmful 
    content and identify sentiment. It requires an API key and endpoint, 
    which can be set up as described in the following guide:
    
    https://learn.microsoft.com/python/api/overview/azure/ai-contentsafety-readme?view=azure-python

    Attributes:
        content_safety_key (str): 
            The API key used to authenticate requests with Azure Content Safety API.
        content_safety_endpoint (str): 
            The endpoint URL for the Azure Content Safety API.
        content_safety_client (Any): 
            An instance of the Azure Content Safety Client used for making API requests.

    Methods:
        validate_environment(values: Dict) -> Dict:
            Validates the presence of API key and endpoint in the environment 
            and initializes the Content Safety Client.

        _sentiment_analysis(text: str) -> Dict:
            Analyzes the provided text to assess its sentiment and safety, 
            returning the analysis results.

        _run(query: str, 
            run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
            Uses the tool to analyze the given query and returns the result. 
            Raises a RuntimeError if an exception occurs.
    """

    content_safety_key: str = ""  #: :meta private:
    content_safety_endpoint: str = ""  #: :meta private:
    content_safety_client: Any  #: :meta private:

    name: str = "azure_content_safety_tool"
    description: str = (
        "A wrapper around Azure AI Content Safety. "
        '''Useful for when you need to identify the sentiment of text
        and whether or not a text is harmful. '''
        "Input should be text."
    )

    @root_validator(pre=True)
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate that api key and endpoint exists in environment."""
        content_safety_key = get_from_dict_or_env(
            values, "content_safety_key", "CONTENT_SAFETY_API_KEY"
        )

        content_safety_endpoint = get_from_dict_or_env(
            values, "content_safety_endpoint", "CONTENT_SAFETY_ENDPOINT"
        )

        try:
            import azure.ai.contentsafety as sdk
            from azure.core.credentials import AzureKeyCredential

            values["content_safety_client"] = sdk.ContentSafetyClient(
                endpoint=content_safety_endpoint,
                credential=AzureKeyCredential(content_safety_key),
            )

        except ImportError:
            raise ImportError(
                "azure-ai-contentsafety is not installed. "
                "Run `pip install azure-ai-contentsafety` to install."
            )

        return values

    def _sentiment_analysis(self, text: str) -> Dict:
        """
        Perform sentiment analysis on the provided text.

        This method uses the Azure Content Safety Client to analyze
        the text and determine its sentiment and safety categories.

        Args:
            text (str): The text to be analyzed.

        Returns:
            Dict: The analysis results containing sentiment and safety categories.
        """
        
        from azure.ai.contentsafety.models import AnalyzeTextOptions

        request = AnalyzeTextOptions(text=text)
        response = self.content_safety_client.analyze_text(request)
        result = response.categories_analysis
        return result

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """
        Analyze the given query using the tool.

        This method calls `_sentiment_analysis` to process the 
        query and returns the result. It raises a RuntimeError if an 
        exception occurs during analysis.

        Args:
            query (str): 
                The query text to be analyzed.
            run_manager (Optional[CallbackManagerForToolRun], optional): 
                A callback manager for tracking the tool run. Defaults to None.

        Returns:
            str: The result of the sentiment analysis.

        Raises:
            RuntimeError: If an error occurs while running the tool.
        """
        try:
            return self._sentiment_analysis(query)
        except Exception as e:
            raise RuntimeError(
                f"Error while running AzureContentSafetyTextTool: {e}"
            )