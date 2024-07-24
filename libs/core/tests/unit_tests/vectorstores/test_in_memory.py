from pathlib import Path

import pytest
from langchain_standard_tests.integration_tests.vectorstores import (
    AsyncReadWriteTestSuite,
    ReadWriteTestSuite,
)
from langchain_core.documents import Document
from langchain_core.embeddings.fake import DeterministicFakeEmbedding
from langchain_core.vectorstores import InMemoryVectorStore
from tests.unit_tests.stubs import AnyStr


class TestInMemoryReadWriteTestSuite(ReadWriteTestSuite):
    @pytest.fixture
    def vectorstore(self) -> InMemoryVectorStore:
        return InMemoryVectorStore(embedding=self.get_embeddings())


class TestAsyncInMemoryReadWriteTestSuite(AsyncReadWriteTestSuite):
    @pytest.fixture
    async def vectorstore(self) -> InMemoryVectorStore:
        return InMemoryVectorStore(embedding=self.get_embeddings())


async def test_inmemory() -> None:
    """Test end to end construction and search."""
    store = await InMemoryVectorStore.afrom_texts(
        ["foo", "bar", "baz"], DeterministicFakeEmbedding(size=6)
    )
    output = await store.asimilarity_search("foo", k=1)
    assert output == [Document(page_content="foo", id=AnyStr())]

    output = await store.asimilarity_search("bar", k=2)
    assert output == [
        Document(page_content="bar", id=AnyStr()),
        Document(page_content="baz", id=AnyStr()),
    ]

    output2 = await store.asimilarity_search_with_score("bar", k=2)
    assert output2[0][1] > output2[1][1]


async def test_add_by_ids() -> None:
    vectorstore = InMemoryVectorStore(embedding=DeterministicFakeEmbedding(size=6))

    # Check sync version
    ids1 = vectorstore.add_texts(["foo", "bar", "baz"], ids=["1", "2", "3"])
    assert ids1 == ["1", "2", "3"]
    assert sorted(vectorstore.store.keys()) == ["1", "2", "3"]

    ids2 = await vectorstore.aadd_texts(["foo", "bar", "baz"], ids=["4", "5", "6"])
    assert ids2 == ["4", "5", "6"]
    assert sorted(vectorstore.store.keys()) == ["1", "2", "3", "4", "5", "6"]


async def test_inmemory_mmr() -> None:
    texts = ["foo", "foo", "fou", "foy"]
    docsearch = await InMemoryVectorStore.afrom_texts(
        texts, DeterministicFakeEmbedding(size=6)
    )
    # make sure we can k > docstore size
    output = await docsearch.amax_marginal_relevance_search(
        "foo", k=10, lambda_mult=0.1
    )
    assert len(output) == len(texts)
    assert output[0] == Document(page_content="foo", id=AnyStr())
    assert output[1] == Document(page_content="foy", id=AnyStr())


async def test_inmemory_dump_load(tmp_path: Path) -> None:
    """Test end to end construction and search."""
    embedding = DeterministicFakeEmbedding(size=6)
    store = await InMemoryVectorStore.afrom_texts(["foo", "bar", "baz"], embedding)
    output = await store.asimilarity_search("foo", k=1)

    test_file = str(tmp_path / "test.json")
    store.dump(test_file)

    loaded_store = InMemoryVectorStore.load(test_file, embedding)
    loaded_output = await loaded_store.asimilarity_search("foo", k=1)

    assert output == loaded_output


async def test_inmemory_filter() -> None:
    """Test end to end construction and search."""
    store = await InMemoryVectorStore.afrom_texts(
        ["foo", "bar"],
        DeterministicFakeEmbedding(size=6),
        [{"id": 1}, {"id": 2}],
    )
    output = await store.asimilarity_search(
        "baz", filter=lambda doc: doc.metadata["id"] == 1
    )
    assert output == [Document(page_content="foo", metadata={"id": 1}, id=AnyStr())]


async def test_get_vector_from_metadata() -> None:
    vectorstore = InMemoryVectorStore(embedding=DeterministicFakeEmbedding(size=6))

    # Check sync version
    ids1 = vectorstore.add_texts(["foo", "bar", "baz"], ids=["1", "2", "3"])
    assert ids1 == ["1", "2", "3"]

    doc = vectorstore.get_by_ids(["1"])
    assert len(doc) == 1

    vector = doc[0].metadata["vector"]
    assert vector is not None and len(vector) == 6
