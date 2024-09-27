"""Wrapper around YandexGPT chat models."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, cast

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from langchain_community.llms.utils import enforce_stop_tokens
from langchain_community.llms.yandex import _BaseYandexGPT

logger = logging.getLogger(__name__)


def _parse_message(role: str, text: str) -> Dict:
    return {"role": role, "text": text}


def _parse_chat_history(history: List[BaseMessage]) -> List[Dict[str, str]]:
    """Parse a sequence of messages into history.

    Returns:
        A list of parsed messages.
    """
    chat_history = []
    for message in history:
        content = cast(str, message.content)
        if isinstance(message, HumanMessage):
            chat_history.append(_parse_message("user", content))
        if isinstance(message, AIMessage):
            chat_history.append(_parse_message("assistant", content))
        if isinstance(message, SystemMessage):
            chat_history.append(_parse_message("system", content))
    return chat_history


class ChatYandexGPT(_BaseYandexGPT, BaseChatModel):
    """YandexGPT large language models.

    There are two authentication options for the service account
    with the ``ai.languageModels.user`` role:
        - You can specify the token in a constructor parameter `iam_token`
        or in an environment variable `YC_IAM_TOKEN`.
        - You can specify the key in a constructor parameter `api_key`
        or in an environment variable `YC_API_KEY`.

    Example:
        .. code-block:: python

            from langchain_community.chat_models import ChatYandexGPT
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
        text = completion_with_retry(self, messages=messages)
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
        """Async method to generate next turn in the conversation.

        Args:
            messages: The history of the conversation as a list of messages.
            stop: The list of stop words (optional).
            run_manager: The CallbackManager for LLM run, it's not used at the moment.

        Returns:
            The ChatResult that contains outputs generated by the model.

        Raises:
            ValueError: if the last message in the list is not from human.
        """
        text = await acompletion_with_retry(self, messages=messages)
        text = text if stop is None else enforce_stop_tokens(text, stop)
        message = AIMessage(content=text)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        stream_resp = completion_with_retry(self, messages=messages, stream=True)
        current_text = ""
        for data in stream_resp:
            delta = data[len(current_text) :]
            current_text = data
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=delta))
            if run_manager:
                run_manager.on_llm_new_token(delta, chunk=chunk)
            yield chunk

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        current_text = ""
        async for data in await acompletion_with_retry(
            self, messages=messages, stream=True
        ):
            delta = data[len(current_text) :]
            current_text = data
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=delta))
            if run_manager:
                run_manager.on_llm_new_token(delta, chunk=chunk)
            yield chunk


def _generate_completion(
    self: ChatYandexGPT, messages: List[BaseMessage], stream: bool = None
):
    try:
        import grpc
        from google.protobuf.wrappers_pb2 import DoubleValue, Int64Value

        try:
            from yandex.cloud.ai.foundation_models.v1.text_common_pb2 import (
                CompletionOptions,
                Message,
            )
            from yandex.cloud.ai.foundation_models.v1.text_generation.text_generation_service_pb2 import (  # noqa: E501
                CompletionRequest,
            )
            from yandex.cloud.ai.foundation_models.v1.text_generation.text_generation_service_pb2_grpc import (  # noqa: E501
                TextGenerationServiceStub,
            )
        except ModuleNotFoundError:
            from yandex.cloud.ai.foundation_models.v1.foundation_models_pb2 import (
                CompletionOptions,
                Message,
            )
            from yandex.cloud.ai.foundation_models.v1.foundation_models_service_pb2 import (  # noqa: E501
                CompletionRequest,
            )
            from yandex.cloud.ai.foundation_models.v1.foundation_models_service_pb2_grpc import (  # noqa: E501
                TextGenerationServiceStub,
            )
    except ImportError as e:
        raise ImportError(
            "Please install YandexCloud SDK  with `pip install yandexcloud` \
            or upgrade it to recent version."
        ) from e
    if not messages:
        raise ValueError("You should provide at least one message to start the chat!")
    message_history = _parse_chat_history(messages)
    channel_credentials = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel(self.url, channel_credentials)
    request = CompletionRequest(
        model_uri=self.model_uri,
        completion_options=CompletionOptions(
            temperature=DoubleValue(value=self.temperature),
            max_tokens=Int64Value(value=self.max_tokens),
            stream=stream,
        ),
        messages=[Message(**message) for message in message_history],
    )
    stub = TextGenerationServiceStub(channel)
    res = stub.Completion(request, metadata=self._grpc_metadata)
    return list(res)[0].alternatives[0].message.text


async def _agenerate_completion(self, messages, stream=False):
    try:
        import asyncio

        import grpc
        from google.protobuf.wrappers_pb2 import DoubleValue, Int64Value

        try:
            from yandex.cloud.ai.foundation_models.v1.text_common_pb2 import (
                CompletionOptions,
                Message,
            )
            from yandex.cloud.ai.foundation_models.v1.text_generation.text_generation_service_pb2 import (  # noqa: E501
                CompletionRequest,
                CompletionResponse,
            )
            from yandex.cloud.ai.foundation_models.v1.text_generation.text_generation_service_pb2_grpc import (  # noqa: E501
                TextGenerationAsyncServiceStub,
            )
        except ModuleNotFoundError:
            from yandex.cloud.ai.foundation_models.v1.foundation_models_pb2 import (
                CompletionOptions,
                Message,
            )
            from yandex.cloud.ai.foundation_models.v1.foundation_models_service_pb2 import (  # noqa: E501
                CompletionRequest,
                CompletionResponse,
            )
            from yandex.cloud.ai.foundation_models.v1.foundation_models_service_pb2_grpc import (  # noqa: E501
                TextGenerationAsyncServiceStub,
            )
        from yandex.cloud.operation.operation_service_pb2 import GetOperationRequest
        from yandex.cloud.operation.operation_service_pb2_grpc import (
            OperationServiceStub,
        )
    except ImportError as e:
        raise ImportError(
            "Please install YandexCloud SDK  with `pip install yandexcloud` \
            or upgrade it to recent version."
        ) from e
    if not messages:
        raise ValueError("You should provide at least one message to start the chat!")
    message_history = _parse_chat_history(messages)
    operation_api_url = "operation.api.cloud.yandex.net:443"
    channel_credentials = grpc.ssl_channel_credentials()

    async with grpc.aio.secure_channel(self.url, channel_credentials) as channel:
        request = CompletionRequest(
            model_uri=self.model_uri,
            completion_options=CompletionOptions(
                temperature=DoubleValue(value=self.temperature),
                max_tokens=Int64Value(value=self.max_tokens),
                stream=stream,  # Use the stream parameter
            ),
            messages=[Message(**message) for message in message_history],
        )
        stub = TextGenerationAsyncServiceStub(channel)
        operation = await stub.Completion(request, metadata=self._grpc_metadata)

        async with grpc.aio.secure_channel(
            operation_api_url, channel_credentials
        ) as operation_channel:
            operation_stub = OperationServiceStub(operation_channel)
            while not operation.done:
                await asyncio.sleep(1)
                operation_request = GetOperationRequest(operation_id=operation.id)
                operation = await operation_stub.Get(
                    operation_request,
                    metadata=self.grpc_metadata,
                )

            completion_response = CompletionResponse()
            operation.response.Unpack(completion_response)

            return completion_response


def _make_request_invoke(
    self: ChatYandexGPT,
    messages: List[BaseMessage],
):
    result = _generate_completion(self, messages, None)
    return list(result)[0].alternatives[0].message.text


def _make_request_stream(
    self: ChatYandexGPT,
    messages: List[BaseMessage],
):
    result = _generate_completion(self, messages, True)
    for chunk in result:
        yield chunk.alternatives[0].message.text


async def _amake_request_invoke(llm: ChatYandexGPT, **kwargs: Any) -> Any:
    result = await _agenerate_completion(llm, stream=None, **kwargs)
    return result.alternatives[0].message.text


async def _amake_request_stream(llm: ChatYandexGPT, **kwargs: Any) -> Any:
    result = await _agenerate_completion(llm, stream=True, **kwargs)
    for alternative in result.alternatives:
        yield alternative.message.text


def _create_retry_decorator(llm: ChatYandexGPT) -> Callable[[Any], Any]:
    from grpc import RpcError

    min_seconds = llm.sleep_interval
    max_seconds = 60
    return retry(
        reraise=True,
        stop=stop_after_attempt(llm.max_retries),
        wait=wait_exponential(multiplier=1, min=min_seconds, max=max_seconds),
        retry=(retry_if_exception_type((RpcError))),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )


def completion_with_retry(
    llm: ChatYandexGPT, stream: bool = False, **kwargs: Any
) -> Any:
    """Use tenacity to retry the completion call."""
    retry_decorator = _create_retry_decorator(llm)

    @retry_decorator
    def _completion_with_retry(**_kwargs: Any) -> Any:
        if stream:
            return _make_request_stream(llm, **_kwargs)
        return _make_request_invoke(llm, **_kwargs)

    return _completion_with_retry(**kwargs)


async def acompletion_with_retry(
    llm: ChatYandexGPT, stream: bool = False, **kwargs: Any
) -> Any:
    """Use tenacity to retry the async completion call."""
    retry_decorator = _create_retry_decorator(llm)

    @retry_decorator
    async def _completion_with_retry(**_kwargs: Any) -> Any:
        if stream:
            return _amake_request_stream(llm, **_kwargs)
        return await _amake_request_invoke(llm, **_kwargs)

    return await _completion_with_retry(**kwargs)
