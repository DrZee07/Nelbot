"""Wrapper around SingleStore DB."""
from __future__ import annotations

import json
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
)

from sqlalchemy.pool import QueuePool

from pydantic import BaseModel, root_validator

from langchain.docstore.document import Document
from langchain.embeddings.base import Embeddings
from langchain.utils import get_from_dict_or_env
from langchain.vectorstores.base import VectorStore, VectorStoreRetriever


class SingleStoreDB(VectorStore):
    """Wrapper around SingleStore DB database.

    To use, you should have the ``singlestoredb`` python package installed.

    Example:
        .. code-block:: python

            from langchain.vectorstores import SingleStoreDB
            from langchain.embeddings import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings()
            vectorstore = SingleStoreDB(
                embedding_function=embeddings.embed_query,
                host="https://user:password@127.0.0.1:3306/database"
            )
    """

    def _get_connection(self: SingleStoreDB) -> Any:
        try:
            import singlestoredb as s2
        except ImportError:
            raise ValueError(
                "Could not import singlestoredb python package. "
                "Please install it with `pip install singlestoredb`."
            )
        return s2.connect(**self.connection_kwargs)

    def __init__(
        self,
        embedding_function: Callable,
        table_name: str = "embeddings",
        content_field: str = "content",
        metadata_field: str = "metadata",
        vector_field: str = "vector",
        pool_size: int = 5,
        max_overflow: int = 10,
        timeout: float = 30,
        **kwargs: Any,
    ):
        """Initialize with necessary components."""

        self.embedding_function = embedding_function
        self.table_name = table_name
        self.content_field = content_field
        self.metadata_field = metadata_field
        self.vector_field = vector_field
        self.connection_kwargs = kwargs
        self.connection_pool = QueuePool(self._get_connection, max_overflow=max_overflow, pool_size=pool_size, timeout=timeout)
        self._create_table()

    def _create_table(self: SingleStoreDB) -> None:
        conn = self.connection_pool.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS {}
                    ({} TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                    {} BLOB, {} JSON);""".format(
                        self.table_name,
                        self.content_field,
                        self.vector_field,
                        self.metadata_field,
                    ),
                )
        finally:
            conn.close()

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        embeddings: Optional[List[List[float]]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """Add more texts to the vectorstore.

        Args:
            texts (Iterable[str]): Iterable of strings/text to add to the vectorstore.
            metadatas (Optional[List[dict]], optional): Optional list of metadatas.
                Defaults to None.
            embeddings (Optional[List[List[float]]], optional): Optional pre-generated
                embeddings. Defaults to None.

        Returns:
            List[str]: empty list
        """
        conn = self.connection_pool.connect()
        try:
            with conn.cursor() as cur:
                # Write data to singlestore db
                for i, text in enumerate(texts):
                    # Use provided values by default or fallback
                    metadata = metadatas[i] if metadatas else {}
                    embedding = (
                        embeddings[i] if embeddings else self.embedding_function(text)
                    )
                    cur.execute(
                        "INSERT INTO {} VALUES (%s, JSON_ARRAY_PACK(%s), %s)".format(
                            self.table_name
                        ),
                        (
                            text,
                            "[{}]".format(",".join(map(str, embedding))),
                            json.dumps(metadata),
                        ),
                    )
        finally:
            conn.close()
        return []

    def similarity_search(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> List[Document]:
        """
        Returns the most similar indexed documents to the query text.

        Args:
            query (str): The query text for which to find similar documents.
            k (int): The number of documents to return. Default is 4.

        Returns:
            List[Document]: A list of documents that are most similar to the query text.
        """
        docs_and_scores = self.similarity_search_with_score(query, k=k)
        return [doc for doc, _ in docs_and_scores]

    def similarity_search_with_score(
        self, query: str, k: int = 4
    ) -> List[Tuple[Document, float]]:
        """Return docs most similar to query.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of Documents most similar to the query and score for each
        """
        # Creates embedding vector from user query
        embedding = self.embedding_function(query)
        conn = self.connection_pool.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT {}, {}, DOT_PRODUCT({}, JSON_ARRAY_PACK(%s)) as __score 
                    FROM {} ORDER BY __score DESC LIMIT %s""".format(
                        self.content_field,
                        self.metadata_field,
                        self.vector_field,
                        self.table_name,
                    ),
                    (
                        "[{}]".format(",".join(map(str, embedding))),
                        k,
                    ),
                )

                result = [
                    (
                        Document(page_content=row[0], metadata=row[1]),
                        float(row[2]),
                    )
                    for row in cur.fetchall()
                ]
        finally:
            conn.close()
        return result

    @classmethod
    def from_texts(
        cls: Type[SingleStoreDB],
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        table_name: str = "embeddings",
        content_field: str = "content",
        metadata_field: str = "metadata",
        vector_field: str = "vector",
        pool_size: int = 5,
        max_overflow: int = 10,
        timeout: float = 30,
        **kwargs: Any,
    ) -> SingleStoreDB:
        """Create a SingleStoreDB vectorstore from raw documents.
        This is a user-friendly interface that:
            1. Embeds documents.
            2. Creates a new table for the embeddings in SingleStoreDB.
            3. Adds the documents to the newly created table.
        This is intended to be a quick way to get started.
        Example:
            .. code-block:: python
                from langchain.vectorstores import SingleStoreDB
                from langchain.embeddings import OpenAIEmbeddings
                embeddings = OpenAIEmbeddings()
                s2 = SingleStoreDB.from_texts(
                    texts,
                    embeddings,
                    host="username:password@localhost:3306/database"
                )
        """


        instance = cls(
            table_name=table_name,
            content_field=content_field,
            metadata_field=metadata_field,
            vector_field=vector_field,
            embedding_function=embedding.embed_query,
            pool_size=pool_size,
            max_overflow=max_overflow,
            timeout=timeout,
            **kwargs,
        )
        instance.add_texts(texts, metadatas, embedding.embed_documents(texts), **kwargs)
        return instance

    def as_retriever(self, **kwargs: Any) -> SingleStoreDBVectorStoreRetriever:
        return SingleStoreDBVectorStoreRetriever(vectorstore=self, **kwargs)


class SingleStoreDBVectorStoreRetriever(VectorStoreRetriever, BaseModel):
    vectorstore: SingleStoreDB
    search_type: str = "similarity"
    k: int = 4
    score_threshold: float = 0.4

    class Config:
        """Configuration for this pydantic object."""

        arbitrary_types_allowed = True

    @root_validator()
    def validate_search_type(cls, values: Dict) -> Dict:
        """Validate search type."""
        if "search_type" in values:
            search_type = values["search_type"]
            if search_type not in ("similarity"):
                raise ValueError(f"search_type of {search_type} not allowed.")
        return values

    def get_relevant_documents(self, query: str) -> List[Document]:
        if self.search_type == "similarity":
            docs = self.vectorstore.similarity_search(query, k=self.k)
        else:
            raise ValueError(f"search_type of {self.search_type} not allowed.")
        return docs

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        raise NotImplementedError(
            "SingleStoreDBVectorStoreRetriever does not support async"
        )

    def add_documents(self, documents: List[Document], **kwargs: Any) -> List[str]:
        """Add documents to vectorstore."""
        return self.vectorstore.add_documents(documents, **kwargs)

    async def aadd_documents(
        self, documents: List[Document], **kwargs: Any
    ) -> List[str]:
        """Add documents to vectorstore."""
        return await self.vectorstore.aadd_documents(documents, **kwargs)
