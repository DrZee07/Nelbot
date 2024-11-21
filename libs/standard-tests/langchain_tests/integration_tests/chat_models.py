import base64
import json
from typing import List, Optional, cast

import httpx
import pytest
from langchain_core.language_models import BaseChatModel, GenericFakeChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    BaseMessageChunk,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from pydantic.v1 import BaseModel as BaseModelV1
from pydantic.v1 import Field as FieldV1

from langchain_tests.unit_tests.chat_models import (
    ChatModelTests,
    my_adder_tool,
)
from langchain_tests.utils.pydantic import PYDANTIC_MAJOR_VERSION


class MagicFunctionSchema(BaseModel):
    input: int = Field(..., gt=-1000, lt=1000)


@tool(args_schema=MagicFunctionSchema)
def magic_function(input: int) -> int:
    """Applies a magic function to an input."""
    return input + 2


@tool
def magic_function_no_args() -> int:
    """Calculates a magic function."""
    return 5


class Joke(BaseModel):
    """Joke to tell user."""

    setup: str = Field(description="question to set up a joke")
    punchline: str = Field(description="answer to resolve the joke")


def _validate_tool_call_message(message: BaseMessage) -> None:
    assert isinstance(message, AIMessage)
    assert len(message.tool_calls) == 1
    tool_call = message.tool_calls[0]
    assert tool_call["name"] == "magic_function"
    assert tool_call["args"] == {"input": 3}
    assert tool_call["id"] is not None
    assert tool_call["type"] == "tool_call"


def _validate_tool_call_message_no_args(message: BaseMessage) -> None:
    assert isinstance(message, AIMessage)
    assert len(message.tool_calls) == 1
    tool_call = message.tool_calls[0]
    assert tool_call["name"] == "magic_function_no_args"
    assert tool_call["args"] == {}
    assert tool_call["id"] is not None
    assert tool_call["type"] == "tool_call"


class ChatModelIntegrationTests(ChatModelTests):
    @property
    def standard_chat_model_params(self) -> dict:
        return {}

    def test_invoke(self, model: BaseChatModel) -> None:
        """Test to verify that `model.invoke(simple_message)` works.

        This should pass for all integrations.

        .. dropdown:: Troubleshooting

            If this test fails, you should make sure your _generate method
            does not raise any exceptions, and that it returns a valid
            :class:`~langchain_core.outputs.chat_result.ChatResult` like so:

            .. code-block:: python

                return ChatResult(
                    generations=[ChatGeneration(
                        message=AIMessage(content="Output text")
                    )]
                )
        """
        result = model.invoke("Hello")
        assert result is not None
        assert isinstance(result, AIMessage)
        assert isinstance(result.content, str)
        assert len(result.content) > 0

    async def test_ainvoke(self, model: BaseChatModel) -> None:
        """Test to verify that `await model.ainvoke(simple_message)` works.

        This should pass for all integrations. Passing this test does not indicate
        a "natively async" implementation, but rather that the model can be used
        in an async context.

        .. dropdown:: Troubleshooting

            First, debug
            :meth:`~langchain_tests.integration_tests.chat_models.ChatModelIntegrationTests.test_invoke`.
            because `ainvoke` has a default implementation that calls `invoke` in an
            async context.

            If that test passes but not this one, you should make sure your _agenerate
            method does not raise any exceptions, and that it returns a valid
            :class:`~langchain_core.outputs.chat_result.ChatResult` like so:

            .. code-block:: python

                return ChatResult(
                    generations=[ChatGeneration(
                        message=AIMessage(content="Output text")
                    )]
                )
        """
        result = await model.ainvoke("Hello")
        assert result is not None
        assert isinstance(result, AIMessage)
        assert isinstance(result.content, str)
        assert len(result.content) > 0

    def test_stream(self, model: BaseChatModel) -> None:
        """Test to verify that `model.stream(simple_message)` works.

        This should pass for all integrations. Passing this test does not indicate
        a "streaming" implementation, but rather that the model can be used in a
        streaming context.

        .. dropdown:: Troubleshooting

            First, debug
            :meth:`~langchain_tests.integration_tests.chat_models.ChatModelIntegrationTests.test_invoke`.
            because `stream` has a default implementation that calls `invoke` and yields
            the result as a single chunk.

            If that test passes but not this one, you should make sure your _stream
            method does not raise any exceptions, and that it yields valid
            :class:`~langchain_core.outputs.chat_generation.ChatGenerationChunk`
            objects like so:

            .. code-block:: python

                yield ChatGenerationChunk(
                    message=AIMessageChunk(content="chunk text")
                )
        """
        num_tokens = 0
        for token in model.stream("Hello"):
            assert token is not None
            assert isinstance(token, AIMessageChunk)
            num_tokens += len(token.content)
        assert num_tokens > 0

    async def test_astream(self, model: BaseChatModel) -> None:
        """Test to verify that `await model.astream(simple_message)` works.

        This should pass for all integrations. Passing this test does not indicate
        a "natively async" or "streaming" implementation, but rather that the model can
        be used in an async streaming context.

        .. dropdown:: Troubleshooting

            First, debug
            :meth:`~langchain_tests.integration_tests.chat_models.ChatModelIntegrationTests.test_stream`.
            and
            :meth:`~langchain_tests.integration_tests.chat_models.ChatModelIntegrationTests.test_ainvoke`.
            because `astream` has a default implementation that calls `_stream` in an
            async context if it is implemented, or `ainvoke` and yields the result as a
            single chunk if not.

            If those tests pass but not this one, you should make sure your _astream
            method does not raise any exceptions, and that it yields valid
            :class:`~langchain_core.outputs.chat_generation.ChatGenerationChunk`
            objects like so:

            .. code-block:: python

                yield ChatGenerationChunk(
                    message=AIMessageChunk(content="chunk text")
                )
        """
        num_tokens = 0
        async for token in model.astream("Hello"):
            assert token is not None
            assert isinstance(token, AIMessageChunk)
            num_tokens += len(token.content)
        assert num_tokens > 0

    def test_batch(self, model: BaseChatModel) -> None:
        """Test to verify that `model.batch([messages])` works.

        This should pass for all integrations. Tests the model's ability to process
        multiple prompts in a single batch.

        .. dropdown:: Troubleshooting

            First, debug
            :meth:`~langchain_tests.integration_tests.chat_models.ChatModelIntegrationTests.test_invoke`
            because `batch` has a default implementation that calls `invoke` for each message
            in the batch.

            If that test passes but not this one, you should make sure your `batch`
            method does not raise any exceptions, and that it returns a list of valid
            :class:`~langchain_core.messages.AIMessage` objects.
        """
        batch_results = model.batch(["Hello", "Hey"])
        assert batch_results is not None
        assert isinstance(batch_results, list)
        assert len(batch_results) == 2
        for result in batch_results:
            assert result is not None
            assert isinstance(result, AIMessage)
            assert isinstance(result.content, str)
            assert len(result.content) > 0

    async def test_abatch(self, model: BaseChatModel) -> None:
        """Test to verify that `await model.abatch([messages])` works.

        This should pass for all integrations. Tests the model's ability to process
        multiple prompts in a single batch asynchronously.

        .. dropdown:: Troubleshooting

            First, debug
            :meth:`~langchain_tests.integration_tests.chat_models.ChatModelIntegrationTests.test_batch`
            and
            :meth:`~langchain_tests.integration_tests.chat_models.ChatModelIntegrationTests.test_ainvoke`
            because `abatch` has a default implementation that calls `ainvoke` for each message
            in the batch.

            If those tests pass but not this one, you should make sure your `abatch`
            method does not raise any exceptions, and that it returns a list of valid
            :class:`~langchain_core.messages.AIMessage` objects.
        """
        batch_results = await model.abatch(["Hello", "Hey"])
        assert batch_results is not None
        assert isinstance(batch_results, list)
        assert len(batch_results) == 2
        for result in batch_results:
            assert result is not None
            assert isinstance(result, AIMessage)
            assert isinstance(result.content, str)
            assert len(result.content) > 0

    def test_conversation(self, model: BaseChatModel) -> None:
        """Test to verify that the model can handle multi-turn conversations.

        This should pass for all integrations. Tests the model's ability to process
        a sequence of alternating human and AI messages as context for generating
        the next response.

        .. dropdown:: Troubleshooting

            First, debug
            :meth:`~langchain_tests.integration_tests.chat_models.ChatModelIntegrationTests.test_invoke`
            because this test also uses `model.invoke()`.

            If that test passes but not this one, you should verify that:
            1. Your model correctly processes the message history
            2. The model maintains appropriate context from previous messages
            3. The response is a valid :class:`~langchain_core.messages.AIMessage`
        """
        messages = [
            HumanMessage("hello"),
            AIMessage("hello"),
            HumanMessage("how are you"),
        ]
        result = model.invoke(messages)
        assert result is not None
        assert isinstance(result, AIMessage)
        assert isinstance(result.content, str)
        assert len(result.content) > 0

    def test_usage_metadata(self, model: BaseChatModel) -> None:
        """Test to verify that the model returns correct usage metadata.

        .. dropdown:: Configuration to test optional feature

            By default, this test is skipped.
            To test this feature, set `returns_usage_metadata` to True in your test
            class:

            .. code-block:: python

                class TestMyChatModelIntegration(ChatModelIntegrationTests):
                    @property
                    def returns_usage_metadata(self) -> bool:
                        return True

        .. dropdown:: Troubleshooting

            If this test fails, verify that:
            1. Your model correctly tracks and returns token usage
            2. All usage metadata fields (input_tokens, output_tokens, total_tokens) are present
            3. Special token counting (audio, reasoning, cache) works if supported
            4. All token counts are non-negative integers
            5. Total tokens equals or exceeds the sum of input and output tokens
        """
        if not self.returns_usage_metadata:
            pytest.skip("Not implemented.")
        result = model.invoke("Hello")
        assert result is not None
        assert isinstance(result, AIMessage)
        assert result.usage_metadata is not None
        assert isinstance(result.usage_metadata["input_tokens"], int)
        assert isinstance(result.usage_metadata["output_tokens"], int)
        assert isinstance(result.usage_metadata["total_tokens"], int)

        if "audio_input" in self.supported_usage_metadata_details["invoke"]:
            msg = self.invoke_with_audio_input()
            assert msg.usage_metadata is not None
            assert msg.usage_metadata["input_token_details"] is not None
            assert isinstance(msg.usage_metadata["input_token_details"]["audio"], int)
            assert msg.usage_metadata["input_tokens"] >= sum(
                (v or 0)  # type: ignore[misc]
                for v in msg.usage_metadata["input_token_details"].values()
            )
        if "audio_output" in self.supported_usage_metadata_details["invoke"]:
            msg = self.invoke_with_audio_output()
            assert msg.usage_metadata is not None
            assert msg.usage_metadata["output_token_details"] is not None
            assert isinstance(msg.usage_metadata["output_token_details"]["audio"], int)
            assert int(msg.usage_metadata["output_tokens"]) >= sum(
                (v or 0)  # type: ignore[misc]
                for v in msg.usage_metadata["output_token_details"].values()
            )
        if "reasoning_output" in self.supported_usage_metadata_details["invoke"]:
            msg = self.invoke_with_reasoning_output()
            assert msg.usage_metadata is not None
            assert msg.usage_metadata["output_token_details"] is not None
            assert isinstance(
                msg.usage_metadata["output_token_details"]["reasoning"],
                int,
            )
            assert msg.usage_metadata["output_tokens"] >= sum(
                (v or 0)  # type: ignore[misc]
                for v in msg.usage_metadata["output_token_details"].values()
            )
        if "cache_read_input" in self.supported_usage_metadata_details["invoke"]:
            msg = self.invoke_with_cache_read_input()
            assert msg.usage_metadata is not None
            assert msg.usage_metadata["input_token_details"] is not None
            assert isinstance(
                msg.usage_metadata["input_token_details"]["cache_read"],
                int,
            )
            assert msg.usage_metadata["input_tokens"] >= sum(
                (v or 0)  # type: ignore[misc]
                for v in msg.usage_metadata["input_token_details"].values()
            )
        if "cache_creation_input" in self.supported_usage_metadata_details["invoke"]:
            msg = self.invoke_with_cache_creation_input()
            assert msg.usage_metadata is not None
            assert msg.usage_metadata["input_token_details"] is not None
            assert isinstance(
                msg.usage_metadata["input_token_details"]["cache_creation"],
                int,
            )
            assert msg.usage_metadata["input_tokens"] >= sum(
                (v or 0)  # type: ignore[misc]
                for v in msg.usage_metadata["input_token_details"].values()
            )

    def test_usage_metadata_streaming(self, model: BaseChatModel) -> None:
        """
        Test to verify that the model returns correct usage metadata in streaming mode.

        .. dropdown:: Configuration to test optional feature

            By default, this test is skipped.
            To test this feature, set `returns_usage_metadata` to True in your test
            class:

            .. code-block:: python

                class TestMyChatModelIntegration(ChatModelIntegrationTests):
                    @property
                    def returns_usage_metadata(self) -> bool:
                        return True

        .. dropdown:: Troubleshooting

            If this test fails, verify that:
            1. Input tokens are only counted once across all chunks
            2. Output tokens are correctly accumulated across chunks
            3. Total tokens reflect the complete conversation
            4. Special token types (audio, reasoning, cache) are tracked if supported
            5. The final aggregated usage metadata matches non-streaming behavior
            6. No double-counting occurs when combining chunks
        """
        if not self.returns_usage_metadata:
            pytest.skip("Not implemented.")
        full: Optional[AIMessageChunk] = None
        for chunk in model.stream("Write me 2 haikus. Only include the haikus."):
            assert isinstance(chunk, AIMessageChunk)
            # only one chunk is allowed to set usage_metadata.input_tokens
            # if multiple do, it's likely a bug that will result in overcounting
            # input tokens
            if full and full.usage_metadata and full.usage_metadata["input_tokens"]:
                assert (
                    not chunk.usage_metadata or not chunk.usage_metadata["input_tokens"]
                ), (
                    "Only one chunk should set input_tokens,"
                    " the rest should be 0 or None"
                )
            full = chunk if full is None else cast(AIMessageChunk, full + chunk)

        assert isinstance(full, AIMessageChunk)
        assert full.usage_metadata is not None
        assert isinstance(full.usage_metadata["input_tokens"], int)
        assert isinstance(full.usage_metadata["output_tokens"], int)
        assert isinstance(full.usage_metadata["total_tokens"], int)

        if "audio_input" in self.supported_usage_metadata_details["stream"]:
            msg = self.invoke_with_audio_input(stream=True)
            assert isinstance(msg.usage_metadata["input_token_details"]["audio"], int)  # type: ignore[index]
        if "audio_output" in self.supported_usage_metadata_details["stream"]:
            msg = self.invoke_with_audio_output(stream=True)
            assert isinstance(msg.usage_metadata["output_token_details"]["audio"], int)  # type: ignore[index]
        if "reasoning_output" in self.supported_usage_metadata_details["stream"]:
            msg = self.invoke_with_reasoning_output(stream=True)
            assert isinstance(
                msg.usage_metadata["output_token_details"]["reasoning"],  # type: ignore[index]
                int,
            )
        if "cache_read_input" in self.supported_usage_metadata_details["stream"]:
            msg = self.invoke_with_cache_read_input(stream=True)
            assert isinstance(
                msg.usage_metadata["input_token_details"]["cache_read"],  # type: ignore[index]
                int,
            )
        if "cache_creation_input" in self.supported_usage_metadata_details["stream"]:
            msg = self.invoke_with_cache_creation_input(stream=True)
            assert isinstance(
                msg.usage_metadata["input_token_details"]["cache_creation"],  # type: ignore[index]
                int,
            )

    def test_stop_sequence(self, model: BaseChatModel) -> None:
        result = model.invoke("hi", stop=["you"])
        assert isinstance(result, AIMessage)

        custom_model = self.chat_model_class(
            **{**self.chat_model_params, "stop": ["you"]}
        )
        result = custom_model.invoke("hi")
        assert isinstance(result, AIMessage)

    def test_tool_calling(self, model: BaseChatModel) -> None:
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")
        if self.tool_choice_value == "tool_name":
            tool_choice: Optional[str] = "magic_function"
        else:
            tool_choice = self.tool_choice_value
        model_with_tools = model.bind_tools([magic_function], tool_choice=tool_choice)

        # Test invoke
        query = "What is the value of magic_function(3)? Use the tool."
        result = model_with_tools.invoke(query)
        _validate_tool_call_message(result)

        # Test stream
        full: Optional[BaseMessageChunk] = None
        for chunk in model_with_tools.stream(query):
            full = chunk if full is None else full + chunk  # type: ignore
        assert isinstance(full, AIMessage)
        _validate_tool_call_message(full)

    async def test_tool_calling_async(self, model: BaseChatModel) -> None:
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")
        if self.tool_choice_value == "tool_name":
            tool_choice: Optional[str] = "magic_function"
        else:
            tool_choice = self.tool_choice_value
        model_with_tools = model.bind_tools([magic_function], tool_choice=tool_choice)

        # Test ainvoke
        query = "What is the value of magic_function(3)? Use the tool."
        result = await model_with_tools.ainvoke(query)
        _validate_tool_call_message(result)

        # Test astream
        full: Optional[BaseMessageChunk] = None
        async for chunk in model_with_tools.astream(query):
            full = chunk if full is None else full + chunk  # type: ignore
        assert isinstance(full, AIMessage)
        _validate_tool_call_message(full)

    def test_tool_calling_with_no_arguments(self, model: BaseChatModel) -> None:
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")

        if self.tool_choice_value == "tool_name":
            tool_choice: Optional[str] = "magic_function_no_args"
        else:
            tool_choice = self.tool_choice_value
        model_with_tools = model.bind_tools(
            [magic_function_no_args], tool_choice=tool_choice
        )
        query = "What is the value of magic_function()? Use the tool."
        result = model_with_tools.invoke(query)
        _validate_tool_call_message_no_args(result)

        full: Optional[BaseMessageChunk] = None
        for chunk in model_with_tools.stream(query):
            full = chunk if full is None else full + chunk  # type: ignore
        assert isinstance(full, AIMessage)
        _validate_tool_call_message_no_args(full)

    def test_bind_runnables_as_tools(self, model: BaseChatModel) -> None:
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")

        prompt = ChatPromptTemplate.from_messages(
            [("human", "Hello. Please respond in the style of {answer_style}.")]
        )
        llm = GenericFakeChatModel(messages=iter(["hello matey"]))
        chain = prompt | llm | StrOutputParser()
        tool_ = chain.as_tool(
            name="greeting_generator",
            description="Generate a greeting in a particular style of speaking.",
        )
        if self.tool_choice_value == "tool_name":
            tool_choice: Optional[str] = "greeting_generator"
        else:
            tool_choice = self.tool_choice_value
        model_with_tools = model.bind_tools([tool_], tool_choice=tool_choice)
        query = "Using the tool, generate a Pirate greeting."
        result = model_with_tools.invoke(query)
        assert isinstance(result, AIMessage)
        assert result.tool_calls
        tool_call = result.tool_calls[0]
        assert tool_call["args"].get("answer_style")
        assert tool_call["type"] == "tool_call"

    def test_structured_output(self, model: BaseChatModel) -> None:
        """Test to verify structured output with a Pydantic model."""
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")

        # Pydantic class
        # Type ignoring since the interface only officially supports pydantic 1
        # or pydantic.v1.BaseModel but not pydantic.BaseModel from pydantic 2.
        # We'll need to do a pass updating the type signatures.
        chat = model.with_structured_output(Joke)  # type: ignore[arg-type]
        result = chat.invoke("Tell me a joke about cats.")
        assert isinstance(result, Joke)

        for chunk in chat.stream("Tell me a joke about cats."):
            assert isinstance(chunk, Joke)

        # Schema
        chat = model.with_structured_output(Joke.model_json_schema())
        result = chat.invoke("Tell me a joke about cats.")
        assert isinstance(result, dict)
        assert set(result.keys()) == {"setup", "punchline"}

        for chunk in chat.stream("Tell me a joke about cats."):
            assert isinstance(chunk, dict)
        assert isinstance(chunk, dict)  # for mypy
        assert set(chunk.keys()) == {"setup", "punchline"}

    async def test_structured_output_async(self, model: BaseChatModel) -> None:
        """Test to verify structured output with a Pydantic model."""
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")

        # Pydantic class
        # Type ignoring since the interface only officially supports pydantic 1
        # or pydantic.v1.BaseModel but not pydantic.BaseModel from pydantic 2.
        # We'll need to do a pass updating the type signatures.
        chat = model.with_structured_output(Joke)  # type: ignore[arg-type]
        result = await chat.ainvoke("Tell me a joke about cats.")
        assert isinstance(result, Joke)

        async for chunk in chat.astream("Tell me a joke about cats."):
            assert isinstance(chunk, Joke)

        # Schema
        chat = model.with_structured_output(Joke.model_json_schema())
        result = await chat.ainvoke("Tell me a joke about cats.")
        assert isinstance(result, dict)
        assert set(result.keys()) == {"setup", "punchline"}

        async for chunk in chat.astream("Tell me a joke about cats."):
            assert isinstance(chunk, dict)
        assert isinstance(chunk, dict)  # for mypy
        assert set(chunk.keys()) == {"setup", "punchline"}

    @pytest.mark.skipif(PYDANTIC_MAJOR_VERSION != 2, reason="Test requires pydantic 2.")
    def test_structured_output_pydantic_2_v1(self, model: BaseChatModel) -> None:
        """Test to verify compatibility with pydantic.v1.BaseModel.

        pydantic.v1.BaseModel is available in the pydantic 2 package.
        """
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")

        class Joke(BaseModelV1):  # Uses langchain_core.pydantic_v1.BaseModel
            """Joke to tell user."""

            setup: str = FieldV1(description="question to set up a joke")
            punchline: str = FieldV1(description="answer to resolve the joke")

        # Pydantic class
        chat = model.with_structured_output(Joke)
        result = chat.invoke("Tell me a joke about cats.")
        assert isinstance(result, Joke)

        for chunk in chat.stream("Tell me a joke about cats."):
            assert isinstance(chunk, Joke)

        # Schema
        chat = model.with_structured_output(Joke.schema())
        result = chat.invoke("Tell me a joke about cats.")
        assert isinstance(result, dict)
        assert set(result.keys()) == {"setup", "punchline"}

        for chunk in chat.stream("Tell me a joke about cats."):
            assert isinstance(chunk, dict)
        assert isinstance(chunk, dict)  # for mypy
        assert set(chunk.keys()) == {"setup", "punchline"}

    def test_structured_output_optional_param(self, model: BaseChatModel) -> None:
        """Test to verify structured output with an optional param."""
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")

        class Joke(BaseModel):
            """Joke to tell user."""

            setup: str = Field(description="question to set up a joke")
            punchline: Optional[str] = Field(
                default=None, description="answer to resolve the joke"
            )

        chat = model.with_structured_output(Joke)  # type: ignore[arg-type]
        setup_result = chat.invoke(
            "Give me the setup to a joke about cats, no punchline."
        )
        assert isinstance(setup_result, Joke)

        joke_result = chat.invoke("Give me a joke about cats, include the punchline.")
        assert isinstance(joke_result, Joke)

    def test_tool_message_histories_string_content(self, model: BaseChatModel) -> None:
        """
        Test that message histories are compatible with string tool contents
        (e.g. OpenAI).
        """
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")
        model_with_tools = model.bind_tools([my_adder_tool])
        function_name = "my_adder_tool"
        function_args = {"a": "1", "b": "2"}

        messages_string_content = [
            HumanMessage("What is 1 + 2"),
            # string content (e.g. OpenAI)
            AIMessage(
                "",
                tool_calls=[
                    {
                        "name": function_name,
                        "args": function_args,
                        "id": "abc123",
                        "type": "tool_call",
                    },
                ],
            ),
            ToolMessage(
                json.dumps({"result": 3}),
                name=function_name,
                tool_call_id="abc123",
            ),
        ]
        result_string_content = model_with_tools.invoke(messages_string_content)
        assert isinstance(result_string_content, AIMessage)

    def test_tool_message_histories_list_content(
        self,
        model: BaseChatModel,
    ) -> None:
        """
        Test that message histories are compatible with list tool contents
        (e.g. Anthropic).
        """
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")
        model_with_tools = model.bind_tools([my_adder_tool])
        function_name = "my_adder_tool"
        function_args = {"a": 1, "b": 2}

        messages_list_content = [
            HumanMessage("What is 1 + 2"),
            # List content (e.g., Anthropic)
            AIMessage(
                [
                    {"type": "text", "text": "some text"},
                    {
                        "type": "tool_use",
                        "id": "abc123",
                        "name": function_name,
                        "input": function_args,
                    },
                ],
                tool_calls=[
                    {
                        "name": function_name,
                        "args": function_args,
                        "id": "abc123",
                        "type": "tool_call",
                    },
                ],
            ),
            ToolMessage(
                json.dumps({"result": 3}),
                name=function_name,
                tool_call_id="abc123",
            ),
        ]
        result_list_content = model_with_tools.invoke(messages_list_content)
        assert isinstance(result_list_content, AIMessage)

    def test_structured_few_shot_examples(self, model: BaseChatModel) -> None:
        """
        Test that model can process few-shot examples with tool calls.
        """
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")
        model_with_tools = model.bind_tools([my_adder_tool], tool_choice="any")
        function_name = "my_adder_tool"
        function_args = {"a": 1, "b": 2}
        function_result = json.dumps({"result": 3})

        messages_string_content = [
            HumanMessage("What is 1 + 2"),
            AIMessage(
                "",
                tool_calls=[
                    {
                        "name": function_name,
                        "args": function_args,
                        "id": "abc123",
                        "type": "tool_call",
                    },
                ],
            ),
            ToolMessage(
                function_result,
                name=function_name,
                tool_call_id="abc123",
            ),
            AIMessage(function_result),
            HumanMessage("What is 3 + 4"),
        ]
        result_string_content = model_with_tools.invoke(messages_string_content)
        assert isinstance(result_string_content, AIMessage)

    def test_image_inputs(self, model: BaseChatModel) -> None:
        if not self.supports_image_inputs:
            return
        image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
        image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")
        message = HumanMessage(
            content=[
                {"type": "text", "text": "describe the weather in this image"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                },
            ],
        )
        model.invoke([message])

    def test_image_tool_message(self, model: BaseChatModel) -> None:
        if not self.supports_image_tool_message:
            return
        image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
        image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")
        messages = [
            HumanMessage("get a random image using the tool and describe the weather"),
            AIMessage(
                [],
                tool_calls=[
                    {"type": "tool_call", "id": "1", "name": "random_image", "args": {}}
                ],
            ),
            ToolMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
                tool_call_id="1",
                name="random_image",
            ),
        ]

        def random_image() -> str:
            """Return a random image."""
            return ""

        model.bind_tools([random_image]).invoke(messages)

    def test_anthropic_inputs(self, model: BaseChatModel) -> None:
        if not self.supports_anthropic_inputs:
            return

        class color_picker(BaseModelV1):
            """Input your fav color and get a random fact about it."""

            fav_color: str

        human_content: List[dict] = [
            {
                "type": "text",
                "text": "what's your favorite color in this image",
            },
        ]
        if self.supports_image_inputs:
            image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
            image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")
            human_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data,
                    },
                }
            )
        messages = [
            SystemMessage("you're a good assistant"),
            HumanMessage(human_content),  # type: ignore[arg-type]
            AIMessage(
                [
                    {"type": "text", "text": "Hmm let me think about that"},
                    {
                        "type": "tool_use",
                        "input": {"fav_color": "green"},
                        "id": "foo",
                        "name": "color_picker",
                    },
                ]
            ),
            HumanMessage(
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": "foo",
                        "content": [
                            {
                                "type": "text",
                                "text": "green is a great pick! that's my sister's favorite color",  # noqa: E501
                            }
                        ],
                        "is_error": False,
                    },
                    {"type": "text", "text": "what's my sister's favorite color"},
                ]
            ),
        ]
        model.bind_tools([color_picker]).invoke(messages)

    def test_tool_message_error_status(self, model: BaseChatModel) -> None:
        """Test that ToolMessage with status='error' can be handled."""
        if not self.has_tool_calling:
            pytest.skip("Test requires tool calling.")
        model_with_tools = model.bind_tools([my_adder_tool])
        messages = [
            HumanMessage("What is 1 + 2"),
            AIMessage(
                "",
                tool_calls=[
                    {
                        "name": "my_adder_tool",
                        "args": {"a": 1},
                        "id": "abc123",
                        "type": "tool_call",
                    },
                ],
            ),
            ToolMessage(
                "Error: Missing required argument 'b'.",
                name="my_adder_tool",
                tool_call_id="abc123",
                status="error",
            ),
        ]
        result = model_with_tools.invoke(messages)
        assert isinstance(result, AIMessage)

    def test_message_with_name(self, model: BaseChatModel) -> None:
        result = model.invoke([HumanMessage("hello", name="example_user")])
        assert result is not None
        assert isinstance(result, AIMessage)
        assert isinstance(result.content, str)
        assert len(result.content) > 0

    def invoke_with_audio_input(self, *, stream: bool = False) -> AIMessage:
        raise NotImplementedError()

    def invoke_with_audio_output(self, *, stream: bool = False) -> AIMessage:
        raise NotImplementedError()

    def invoke_with_reasoning_output(self, *, stream: bool = False) -> AIMessage:
        raise NotImplementedError()

    def invoke_with_cache_read_input(self, *, stream: bool = False) -> AIMessage:
        raise NotImplementedError()

    def invoke_with_cache_creation_input(self, *, stream: bool = False) -> AIMessage:
        raise NotImplementedError()
