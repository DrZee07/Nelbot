import json
import os
from unittest.mock import patch

import pytest  # type: ignore[import-not-found]
from langchain_core.messages import (
    AIMessage,
    FunctionMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai.chat_models.base import (
    _convert_dict_to_message,
    _convert_message_to_dict,
)

from langchain_pipeshift import ChatPipeshift


def test_initialization() -> None:
    """Test chat model initialization."""
    with patch.dict(os.environ, {"PIPESHIFT_API_KEY": "dummy_key"}):
        ChatPipeshift()


def test_pipeshift_model_param() -> None:
    with patch.dict(os.environ, {"PIPESHIFT_API_KEY": "dummy_key"}):
        llm = ChatPipeshift(model="foo")
        assert llm.model_name == "foo"
        llm = ChatPipeshift(model_name="foo")  # type: ignore[call-arg]
        assert llm.model_name == "foo"
        ls_params = llm._get_ls_params()
        assert ls_params["ls_provider"] == "pipeshift"


def test_function_dict_to_message_function_message() -> None:
    content = json.dumps({"result": "Example #1"})
    name = "test_function"
    result = _convert_dict_to_message(
        {
            "role": "function",
            "name": name,
            "content": content,
        }
    )
    assert isinstance(result, FunctionMessage)
    assert result.name == name
    assert result.content == content


def test_convert_dict_to_message_human() -> None:
    message = {"role": "user", "content": "foo"}
    result = _convert_dict_to_message(message)
    expected_output = HumanMessage(content="foo")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test__convert_dict_to_message_human_with_name() -> None:
    message = {"role": "user", "content": "foo", "name": "test"}
    result = _convert_dict_to_message(message)
    expected_output = HumanMessage(content="foo", name="test")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test_convert_dict_to_message_ai() -> None:
    message = {"role": "assistant", "content": "foo"}
    result = _convert_dict_to_message(message)
    expected_output = AIMessage(content="foo")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test_convert_dict_to_message_ai_with_name() -> None:
    message = {"role": "assistant", "content": "foo", "name": "test"}
    result = _convert_dict_to_message(message)
    expected_output = AIMessage(content="foo", name="test")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test_convert_dict_to_message_system() -> None:
    message = {"role": "system", "content": "foo"}
    result = _convert_dict_to_message(message)
    expected_output = SystemMessage(content="foo")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test_convert_dict_to_message_system_with_name() -> None:
    message = {"role": "system", "content": "foo", "name": "test"}
    result = _convert_dict_to_message(message)
    expected_output = SystemMessage(content="foo", name="test")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


def test_convert_dict_to_message_tool() -> None:
    message = {"role": "tool", "content": "foo", "tool_call_id": "bar"}
    result = _convert_dict_to_message(message)
    expected_output = ToolMessage(content="foo", tool_call_id="bar")
    assert result == expected_output
    assert _convert_message_to_dict(expected_output) == message


@pytest.fixture
def mock_completion() -> dict:
    return {
        "id": "chatcmpl-8bfDvknQda3SQ",
        "object": "chat.completion",
        "created": 1288983000,
        "model": "meta-llama/Llama-2-7b-chat-hf",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello",
                    "name": "Ironyman",
                },
                "finish_reason": "stop",
            }
        ],
    }
