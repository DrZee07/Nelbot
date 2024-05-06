from langchain_together import ChatTogether, TogetherEmbeddings


def test_chat_upstage_secrets() -> None:
    o = ChatTogether(together_api_key="foo")
    s = str(o)
    assert "foo" not in s


def test_upstage_embeddings_secrets() -> None:
    o = TogetherEmbeddings(together_api_key="foo")
    s = str(o)
    assert "foo" not in s
