import pytest

from langchain_cli.namespaces.migrate.generate.partner import (
    get_migrations_for_partner_package,
)

pytest.importorskip(modname="langchain_openai")


def test_generate_migrations() -> None:
    migrations = get_migrations_for_partner_package("langchain_openai")
    assert migrations == [
        ("langchain_community.llms.openai.OpenAI", "langchain_openai.OpenAI"),
        ("langchain_community.llms.openai.AzureOpenAI", "langchain_openai.AzureOpenAI"),
        (
            "langchain_community.embeddings.openai.OpenAIEmbeddings",
            "langchain_openai.OpenAIEmbeddings",
        ),
        (
            "langchain_community.embeddings.azure_openai.AzureOpenAIEmbeddings",
            "langchain_openai.AzureOpenAIEmbeddings",
        ),
        (
            "langchain_community.chat_models.openai.ChatOpenAI",
            "langchain_openai.ChatOpenAI",
        ),
        (
            "langchain_community.chat_models.azure_openai.AzureChatOpenAI",
            "langchain_openai.AzureChatOpenAI",
        ),
    ]
