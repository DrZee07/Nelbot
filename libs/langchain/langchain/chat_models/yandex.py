"""Wrapper around YandexGPT chat models."""
import logging
from typing import Any, Dict, List, Optional, Tuple

from langchain.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain.chat_models.base import BaseChatModel
from langchain.llms.utils import enforce_stop_tokens
from langchain.llms.yandex import BaseYandexGPT
from langchain.schema import (
    AIMessage,
    BaseMessage,
    ChatGeneration,
    ChatResult,
    HumanMessage,
    SystemMessage,
)

logger = logging.getLogger(__name__)


def _parse_message(role: str, text: str) -> Dict:
    return {"role": role, "text": text}


def _parse_chat_history(history: List[BaseMessage]) -> Tuple[List[Dict[str, str]], str]:
    """Parse a sequence of messages into history.

    Returns:
        A tuple of a list of parsed messages and an instruction message for the model.
    """
    chat_history = []
    instruction = ""
    for message in history:
        if isinstance(message, HumanMessage):
            chat_history.append(_parse_message("user", message.content))
        if isinstance(message, AIMessage):
            chat_history.append(_parse_message("assistant", message.content))
        if isinstance(message, SystemMessage):
            instruction = message.content
    return chat_history, instruction


class ChatYandexGPT(BaseYandexGPT, BaseChatModel):
    """Wrapper around YandexGPT large language models.

    To use, you should have the ``yandexcloud`` python package installed, and the
    environment variable ``IAM_TOKEN`` set with IAM token
    for the service account with the ``ai.languageModels.user`` role, or pass
    it as a named parameter ``iam_token`` to the constructor.

    Example:
        .. code-block:: python

            from langchain.chat_models import ChatYandexGPT
            chat_model = ChatYandexGPT(iam_token="t1.9eu...")

    """

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate next turn in the conversation.
        Args:
            messages: The history of the conversation as a list of messages.
            stop: The list of stop words (optional).
            run_manager: The CallbackManager for LLM run, it's not used at the moment.

        Returns:
            The ChatResult that contains outputs generated by the model.

        Raises:
            ValueError: if the last message in the list is not from human.
        """
        try:
            from google.protobuf.wrappers_pb2 import DoubleValue, Int64Value
            from yandex.cloud.ai.llm.v1alpha.llm_pb2 import GenerationOptions, Message
            from yandex.cloud.ai.llm.v1alpha.llm_service_pb2 import ChatRequest
            from yandex.cloud.ai.llm.v1alpha.llm_service_pb2_grpc import (
                TextGenerationServiceStub,
            )
            from yandexcloud import SDK
        except ImportError as e:
            raise ImportError(
                "Please install YandexCloud SDK" " with `pip install yandexcloud`."
            ) from e
        if not messages:
            raise ValueError(
                "You should provide at least one message to start the chat!"
            )
        message_history, instruction = _parse_chat_history(messages)
        request = ChatRequest(
            model=self.model_name,
            generation_options=GenerationOptions(
                temperature=DoubleValue(value=self.temperature),
                max_tokens=Int64Value(value=self.max_tokens),
            ),
            instruction_text=instruction,
            messages=[Message(**message) for message in message_history],
        )
        sdk = SDK(iam_token=self.iam_token)
        operation = sdk.client(TextGenerationServiceStub).Chat(request)
        text = list(operation)[0].message.text
        text = text if stop is None else enforce_stop_tokens(text, stop)
        message = AIMessage(content=text)
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError(
            """YandexGPT doesn't support async requests at the moment."""
        )
