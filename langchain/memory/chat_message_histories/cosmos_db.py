"""Azure CosmosDB Memory History."""
import logging
from typing import Optional

from azure.cosmos import ContainerProxy, CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.identity import DefaultAzureCredential

from langchain.schema import (
    AIMessage,
    BaseChatMessageHistory,
    BaseMessage,
    HumanMessage,
    messages_from_dict,
    messages_to_dict,
)

logger = logging.getLogger(__name__)


class CosmosDBChatMessageHistory(BaseChatMessageHistory):
    """Chat history backed by Azure CosmosDB."""

    def __init__(
        self,
        cosmos_endpoint: str,
        cosmos_database: str,
        cosmos_container: str,
        credential: DefaultAzureCredential,
        session_id: str,
        user_id: str,
        ttl: Optional[int] = None,
    ):
        """
        Initializes a new instance of the CosmosDBChatMessageHistory class.

        :param cosmos_endpoint: The connection endpoint for the Azure Cosmos DB account.
        :param cosmos_database: The name of the database to use.
        :param cosmos_container: The name of the container to use.
        :param credential: The credential to use to authenticate to Azure Cosmos DB.
        :param session_id: The session ID to use, can be overwritten while loading.
        :param user_id: The user ID to use, can be overwritten while loading.
        :param ttl: The time to live (in seconds) to use for documents in the container.
        """
        self.cosmos_endpoint = cosmos_endpoint
        self.cosmos_database = cosmos_database
        self.cosmos_container = cosmos_container
        self.credential = credential
        self.session_id = session_id
        self.user_id = user_id
        self.ttl = ttl

        self._client = CosmosClient(
            url=self.cosmos_endpoint, credential=self.credential
        )
        self._container: Optional["ContainerProxy"] = None

    def __enter__(self) -> "CosmosDBChatMessageHistory":
        """Async context manager entry point."""
        self._client.__enter__()
        database = self._client.create_database_if_not_exists(self.cosmos_database)
        self._container = database.create_container_if_not_exists(
            self.cosmos_container,
            partition_key=PartitionKey("/user_id"),
            default_ttl=self.ttl,
        )
        self.load_messages()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        self.upsert_messages()
        self._client.__exit__(exc_type, exc_val, exc_tb)

    def load_messages(self) -> None:
        """Retrieve the messages from Cosmos"""
        if not self._container:
            raise ValueError("Container not initialized")
        try:
            item = self._container.read_item(
                item=self.session_id, partition_key=self.user_id
            )
        except CosmosHttpResponseError:
            logger.info("no session found")
            return
        if (
            "messages" in item
            and len(item["messages"]) > 0
            and isinstance(item["messages"][0], list)
        ):
            self.messages = messages_from_dict(item["messages"])

    def add_user_message(self, message: str) -> None:
        """Add a user message to the memory."""
        self.upsert_messages(HumanMessage(content=message))

    def add_ai_message(self, message: str) -> None:
        """Add a AI message to the memory."""
        self.upsert_messages(AIMessage(content=message))

    def upsert_messages(self, new_message: Optional[BaseMessage] = None) -> None:
        """Update the cosmosdb item."""
        if new_message:
            self.messages.append(new_message)
        if not self._container:
            raise ValueError("Container not initialized")
        self._container.upsert_item(
            body={
                "id": self.session_id,
                "user_id": self.user_id,
                "messages": messages_to_dict(self.messages),
            }
        )

    def clear(self) -> None:
        """Clear session memory from this memory and cosmos."""
        self.messages = []
        if self._container:
            self._container.delete_item(
                item=self.session_id, partition_key=self.user_id
            )
