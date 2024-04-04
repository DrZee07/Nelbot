import os
import re
import warnings
from operator import itemgetter
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypedDict,
    Union,
    cast,
)

import anthropic
from langchain_core._api import beta, deprecated
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import (
    BaseChatModel,
    agenerate_from_stream,
    generate_from_stream,
)
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.pydantic_v1 import BaseModel, Field, SecretStr, root_validator
from langchain_core.runnables import (
    Runnable,
    RunnableMap,
    RunnablePassthrough,
)
from langchain_core.tools import BaseTool
from langchain_core.utils import (
    build_extra_kwargs,
    convert_to_secret_str,
    get_pydantic_field_names,
)
from langchain_core.utils.function_calling import convert_to_openai_tool

from langchain_anthropic.output_parsers import ToolsOutputParser

_message_type_lookups = {"human": "user", "ai": "assistant"}


def _format_image(image_url: str) -> Dict:
    """
    Formats an image of format data:image/jpeg;base64,{b64_string}
    to a dict for anthropic api

    {
      "type": "base64",
      "media_type": "image/jpeg",
      "data": "/9j/4AAQSkZJRg...",
    }

    And throws an error if it's not a b64 image
    """
    regex = r"^data:(?P<media_type>image/.+);base64,(?P<data>.+)$"
    match = re.match(regex, image_url)
    if match is None:
        raise ValueError(
            "Anthropic only supports base64-encoded images currently."
            " Example: data:image/png;base64,'/9j/4AAQSk'..."
        )
    return {
        "type": "base64",
        "media_type": match.group("media_type"),
        "data": match.group("data"),
    }


def _merge_messages(
    messages: List[BaseMessage],
) -> List[Union[SystemMessage, AIMessage, HumanMessage]]:
    """Merge runs of human/tool messages into single human messages with content blocks."""  # noqa: E501
    merged: list = []
    for curr in messages:
        if isinstance(curr, ToolMessage):
            if isinstance(curr.content, str):
                curr = HumanMessage(
                    [
                        {
                            "type": "tool_result",
                            "content": curr.content,
                            "tool_use_id": curr.tool_call_id,
                        }
                    ]
                )
            else:
                curr = HumanMessage(curr.content)
        last = merged[-1] if merged else None
        if isinstance(last, HumanMessage) and isinstance(curr, HumanMessage):
            if isinstance(last.content, str):
                new_content: List = [{"type": "text", "text": last.content}]
            else:
                new_content = last.content
            if isinstance(curr.content, str):
                new_content.append({"type": "text", "text": curr.content})
            else:
                new_content.extend(curr.content)
            last.content = new_content
        else:
            merged.append(curr)
    return merged


def _format_messages(messages: List[BaseMessage]) -> Tuple[Optional[str], List[Dict]]:
    """Format messages for anthropic."""

    """
    [
                {
                    "role": _message_type_lookups[m.type],
                    "content": [_AnthropicMessageContent(text=m.content).dict()],
                }
                for m in messages
            ]
    """
    system: Optional[str] = None
    formatted_messages: List[Dict] = []

    merged_messages = _merge_messages(messages)
    for i, message in enumerate(merged_messages):
        if message.type == "system":
            if i != 0:
                raise ValueError("System message must be at beginning of message list.")
            if not isinstance(message.content, str):
                raise ValueError(
                    "System message must be a string, "
                    f"instead was: {type(message.content)}"
                )
            system = message.content
            continue

        role = _message_type_lookups[message.type]
        content: Union[str, List[Dict]]

        if not isinstance(message.content, str):
            # parse as dict
            assert isinstance(
                message.content, list
            ), "Anthropic message content must be str or list of dicts"

            # populate content
            content = []
            for item in message.content:
                if isinstance(item, str):
                    content.append(
                        {
                            "type": "text",
                            "text": item,
                        }
                    )
                elif isinstance(item, dict):
                    if "type" not in item:
                        raise ValueError("Dict content item must have a type key")
                    elif item["type"] == "image_url":
                        # convert format
                        source = _format_image(item["image_url"]["url"])
                        content.append(
                            {
                                "type": "image",
                                "source": source,
                            }
                        )
                    elif item["type"] == "tool_use":
                        item.pop("text", None)
                        content.append(item)
                    else:
                        content.append(item)
                else:
                    raise ValueError(
                        f"Content items must be str or dict, instead was: {type(item)}"
                    )
        else:
            content = message.content

        formatted_messages.append(
            {
                "role": role,
                "content": content,
            }
        )
    return system, formatted_messages


class ChatAnthropic(BaseChatModel):
    """Anthropic chat model.

    To use, you should have the environment variable ``ANTHROPIC_API_KEY``
    set with your API key, or pass it as a named parameter to the constructor.

    Example:
        .. code-block:: python

            from langchain_anthropic import ChatAnthropic

            model = ChatAnthropic(model='claude-3-opus-20240229')
    """

    class Config:
        """Configuration for this pydantic object."""

        allow_population_by_field_name = True

    _client: anthropic.Client = Field(default=None)
    _async_client: anthropic.AsyncClient = Field(default=None)

    model: str = Field(alias="model_name")
    """Model name to use."""

    max_tokens: int = Field(default=1024, alias="max_tokens_to_sample")
    """Denotes the number of tokens to predict per generation."""

    temperature: Optional[float] = None
    """A non-negative float that tunes the degree of randomness in generation."""

    top_k: Optional[int] = None
    """Number of most likely tokens to consider at each step."""

    top_p: Optional[float] = None
    """Total probability mass of tokens to consider at each step."""

    default_request_timeout: Optional[float] = None
    """Timeout for requests to Anthropic Completion API. Default is 600 seconds."""

    anthropic_api_url: str = "https://api.anthropic.com"

    anthropic_api_key: Optional[SecretStr] = None

    default_headers: Optional[Mapping[str, str]] = None
    """Headers to pass to the Anthropic clients, will be used for every API call."""

    model_kwargs: Dict[str, Any] = Field(default_factory=dict)

    streaming: bool = False
    """Whether to use streaming or not."""

    @property
    def _llm_type(self) -> str:
        """Return type of chat model."""
        return "anthropic-chat"

    @root_validator(pre=True)
    def build_extra(cls, values: Dict) -> Dict:
        extra = values.get("model_kwargs", {})
        all_required_field_names = get_pydantic_field_names(cls)
        values["model_kwargs"] = build_extra_kwargs(
            extra, values, all_required_field_names
        )
        return values

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        anthropic_api_key = convert_to_secret_str(
            values.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY") or ""
        )
        values["anthropic_api_key"] = anthropic_api_key
        api_key = anthropic_api_key.get_secret_value()
        api_url = (
            values.get("anthropic_api_url")
            or os.environ.get("ANTHROPIC_API_URL")
            or "https://api.anthropic.com"
        )
        values["anthropic_api_url"] = api_url
        values["_client"] = anthropic.Client(
            api_key=api_key,
            base_url=api_url,
            default_headers=values.get("default_headers"),
        )
        values["_async_client"] = anthropic.AsyncClient(
            api_key=api_key,
            base_url=api_url,
            default_headers=values.get("default_headers"),
        )
        return values

    def _format_params(
        self,
        *,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Dict,
    ) -> Dict:
        # get system prompt if any
        system, formatted_messages = _format_messages(messages)
        rtn = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": formatted_messages,
            "temperature": self.temperature,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "stop_sequences": stop,
            "system": system,
            **self.model_kwargs,
            **kwargs,
        }
        rtn = {k: v for k, v in rtn.items() if v is not None}

        return rtn

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        params = self._format_params(messages=messages, stop=stop, **kwargs)
        if "extra_body" in params and params["extra_body"].get("tools"):
            warnings.warn("stream: Tool use is not yet supported in streaming mode.")
            result = self._generate(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
            yield cast(ChatGenerationChunk, result.generations[0])
            return
        with self._client.messages.stream(**params) as stream:
            for text in stream.text_stream:
                chunk = ChatGenerationChunk(message=AIMessageChunk(content=text))
                if run_manager:
                    run_manager.on_llm_new_token(text, chunk=chunk)
                yield chunk

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        params = self._format_params(messages=messages, stop=stop, **kwargs)
        if "extra_body" in params and params["extra_body"].get("tools"):
            warnings.warn("stream: Tool use is not yet supported in streaming mode.")
            result = await self._agenerate(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
            yield cast(ChatGenerationChunk, result.generations[0])
            return
        async with self._async_client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                chunk = ChatGenerationChunk(message=AIMessageChunk(content=text))
                if run_manager:
                    await run_manager.on_llm_new_token(text, chunk=chunk)
                yield chunk

    def _format_output(self, data: Any, **kwargs: Any) -> ChatResult:
        data_dict = data.model_dump()
        content = data_dict["content"]
        llm_output = {
            k: v for k, v in data_dict.items() if k not in ("content", "role", "type")
        }
        if len(content) == 1 and content[0]["type"] == "text":
            msg = AIMessage(content=content[0]["text"])
        else:
            msg = AIMessage(content=content)
        return ChatResult(
            generations=[ChatGeneration(message=msg)],
            llm_output=llm_output,
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        params = self._format_params(messages=messages, stop=stop, **kwargs)
        if self.streaming:
            if "extra_body" in params and params["extra_body"].get("tools"):
                warnings.warn(
                    "stream: Tool use is not yet supported in streaming mode."
                )
            else:
                stream_iter = self._stream(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
                return generate_from_stream(stream_iter)
        data = self._client.messages.create(**params)
        return self._format_output(data, **kwargs)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        params = self._format_params(messages=messages, stop=stop, **kwargs)
        if self.streaming:
            if "extra_body" in params and params["extra_body"].get("tools"):
                warnings.warn(
                    "stream: Tool use is not yet supported in streaming mode."
                )
            else:
                stream_iter = self._astream(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
                return await agenerate_from_stream(stream_iter)
        data = await self._async_client.messages.create(**params)
        return self._format_output(data, **kwargs)

    @beta()
    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], Type[BaseModel], Callable, BaseTool]],
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """Bind tool-like objects to this chat model.

        Args:
            tools: A list of tool definitions to bind to this chat model.
                Can be  a dictionary, pydantic model, callable, or BaseTool. Pydantic
                models, callables, and BaseTools will be automatically converted to
                their schema dictionary representation.
            **kwargs: Any additional parameters to bind.
        """
        formatted_tools = [convert_to_anthropic_tool(tool) for tool in tools]
        extra_body = kwargs.pop("extra_body", {})
        extra_body["tools"] = formatted_tools
        return self.bind(extra_body=extra_body, **kwargs)

    @beta()
    def with_structured_output(
        self,
        schema: Union[Dict, Type[BaseModel]],
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, Union[Dict, BaseModel]]:
        llm = self.bind_tools([schema])
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            output_parser = ToolsOutputParser(
                first_tool_only=True, pydantic_schemas=[schema]
            )
        else:
            output_parser = ToolsOutputParser(first_tool_only=True, args_only=True)

        if include_raw:
            parser_assign = RunnablePassthrough.assign(
                parsed=itemgetter("raw") | output_parser, parsing_error=lambda _: None
            )
            parser_none = RunnablePassthrough.assign(parsed=lambda _: None)
            parser_with_fallback = parser_assign.with_fallbacks(
                [parser_none], exception_key="parsing_error"
            )
            return RunnableMap(raw=llm) | parser_with_fallback
        else:
            return llm | output_parser


class AnthropicTool(TypedDict):
    name: str
    description: str
    input_schema: Dict[str, Any]


def convert_to_anthropic_tool(
    tool: Union[Dict[str, Any], Type[BaseModel], Callable, BaseTool],
) -> AnthropicTool:
    # already in Anthropic tool format
    if isinstance(tool, dict) and all(
        k in tool for k in ("name", "description", "input_schema")
    ):
        return AnthropicTool(tool)  # type: ignore
    else:
        formatted = convert_to_openai_tool(tool)["function"]
        return AnthropicTool(
            name=formatted["name"],
            description=formatted["description"],
            input_schema=formatted["parameters"],
        )


@deprecated(since="0.1.0", removal="0.2.0", alternative="ChatAnthropic")
class ChatAnthropicMessages(ChatAnthropic):
    pass
