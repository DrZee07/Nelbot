"""Wrapper around DeepInfra APIs."""
from typing import Any, Dict, List, Mapping, Optional

import requests
from pydantic import Extra, root_validator

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from langchain.llms.utils import enforce_stop_tokens
from langchain.utils import get_from_dict_or_env

DEFAULT_MODEL_ID = "google/flan-t5-xl"


class DeepInfra(LLM):
    """Wrapper around DeepInfra deployed models.

    To use, you should have the ``requests`` python package installed, and the
    environment variable ``DEEPINFRA_API_TOKEN`` set with your API token, or pass
    it as a named parameter to the constructor.

    Only supports `text-generation` and `text2text-generation` for now.

    Example:
        .. code-block:: python

            from langchain.llms import DeepInfra
            di = DeepInfra(model_id="google/flan-t5-xl",
                                deepinfra_api_token="my-api-key")
    """

    model_id: str = DEFAULT_MODEL_ID
    model_kwargs: Optional[dict] = None

    deepinfra_api_token: Optional[str] = None

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate that api key and python package exists in environment."""
        deepinfra_api_token = get_from_dict_or_env(
            values, "deepinfra_api_token", "DEEPINFRA_API_TOKEN"
        )
        values["deepinfra_api_token"] = deepinfra_api_token
        return values

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {
            **{"model_id": self.model_id},
            **{"model_kwargs": self.model_kwargs},
        }

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "deepinfra"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> str:
        """Call out to DeepInfra's inference API endpoint.

        Args:
            prompt: The prompt to pass into the model.
            stop: Optional list of stop words to use when generating.

        Returns:
            The string generated by the model.

        Example:
            .. code-block:: python

                response = di("Tell me a joke.")
        """
        _model_kwargs = self.model_kwargs or {}

        res = requests.post(
            f"https://api.deepinfra.com/v1/inference/{self.model_id}",
            headers={
                "Authorization": f"bearer {self.deepinfra_api_token}",
                "Content-Type": "application/json",
            },
            json={"input": prompt, **_model_kwargs},
        )

        if res.status_code != 200:
            raise ValueError("Error raised by inference API")
        t = res.json()
        text = t["results"][0]["generated_text"]

        if stop is not None:
            # I believe this is required since the stop tokens
            # are not enforced by the model parameters
            text = enforce_stop_tokens(text, stop)
        return text
