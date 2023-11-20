"""Test GooseAI"""

import pytest
from langchain_core.pydantic_v1 import SecretStr
from langchain.utils.openai import is_openai_v1
from pytest import MonkeyPatch

from langchain.llms.gooseai import GooseAI


def _openai_v1_installed() -> bool:
    try:
        return is_openai_v1()
    except Exception as _:
        return False


@pytest.mark.requires("openai")
def test_api_key_is_secret_string() -> None:
    llm = GooseAI(gooseai_api_key="secret-api-key")
    assert isinstance(llm.gooseai_api_key, SecretStr)
    assert llm.gooseai_api_key.get_secret_value() == "secret-api-key"


@pytest.mark.skipif(
    _openai_v1_installed(), reason="GooseAI currently only works with openai<1"
)
@pytest.mark.requires("openai")
def test_api_key_masked_when_passed_via_constructor() -> None:
    llm = GooseAI(gooseai_api_key="secret-api-key")
    assert str(llm.gooseai_api_key) == "**********"
    assert "secret-api-key" not in repr(llm.gooseai_api_key)
    assert "secret-api-key" not in repr(llm)


@pytest.mark.skipif(
    _openai_v1_installed(), reason="GooseAI currently only works with openai<1"
)
@pytest.mark.requires("openai")
def test_api_key_masked_when_passed_from_env() -> None:
    with MonkeyPatch.context() as mp:
        mp.setenv("GOOSEAI_API_KEY", "secret-api-key")
        llm = GooseAI()
        assert str(llm.gooseai_api_key) == "**********"
        assert "secret-api-key" not in repr(llm.gooseai_api_key)
        assert "secret-api-key" not in repr(llm)
