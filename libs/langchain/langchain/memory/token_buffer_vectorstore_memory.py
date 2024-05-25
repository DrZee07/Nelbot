"""
Class for a conversation memory buffer with older messages stored in a vectorstore .

This implementats a conversation memory in which the messages are stored in a memory
buffer up to a specified token limit. When the limit is exceeded, older messages are
saved to a vectorstore backing database. The vectorstore can be made persistent across
sessions.
"""

import warnings
from datetime import datetime
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage
from langchain_core.prompts.chat import SystemMessagePromptTemplate
from langchain_core.pydantic_v1 import Field, PrivateAttr
from langchain_core.vectorstores import VectorStoreRetriever

from langchain.memory import ConversationTokenBufferMemory, VectorStoreRetrieverMemory
from langchain.memory.chat_memory import BaseChatMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter

DEFAULT_HISTORY_TEMPLATE = """
Potentially relevant excerpts of previous conversations (timestamped):
{previous_history}

(You do not need to use these pieces of information if not relevant.)

Current date and time: {current_time}.

Current conversation:
"""

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %Z"


class ConversationTokenBufferVectorStoreMemory(ConversationTokenBufferMemory):
    """Conversation chat memory with token limit and vectordb backing.

    load_memory_variables() will return a dict with the key "history".
    It contains background information retrieved from the vector store
    plus recent lines of the current conversation.

    To help the LLM understand the part of the conversation stored in the
    vectorstore, each interaction is timestamped and the current date and
    time is also provided in the history. A side effect of this is that the
    LLM will have access to the current date and time.

    Initialization arguments:

    This class accepts all the initialization arguments of
    ConversationTokenBufferMemory, such as `llm`. In addition, it
    accepts the following additional arguments

        retriever: (required) A VectorStoreRetriever object to use
                   as the vector backing store

        split_chunk_size: (optional, 1000) Token chunk split size
                          for long messages generated by the AI

        previous_history_template: (optional) Template used to format
                                   the contents of the prompt history


    Example using ChromaDB:

        from langchain.memory.token_buffer_vectorstore_memory import (
                ConversationTokenBufferVectorStoreMemory
        )
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import HuggingFaceInstructEmbeddings
        from langchain_openai import OpenAI

        embedder = HuggingFaceInstructEmbeddings(
                        query_instruction="Represent the query for retrieval: "
        )
        chroma = Chroma(collection_name="demo",
                        embedding_function=embedder,
                        collection_metadata={"hnsw:space": "cosine"},
                        )

         retriever = chroma.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    'k': 5,
                    'score_threshold': 0.75,
                },
         )

         conversation_memory = ConversationTokenBufferVectorStoreMemory(
                return_messages=True,
                llm=OpenAI(),
                retriever=retriever,
                max_token_limit = 1000,
         )

         conversation_memory.save_context({"Human": "Hi there"},
                                          {"AI": "Nice to meet you!"}
         )
         conversation_memory.save_context({"Human": "Nice day isn't it?"},
                                          {"AI": "I love Wednesdays."}
         )
         conversation_memory.load_memory_variables({"input": "What time is it?"})

    """

    retriever: VectorStoreRetriever = Field(exclude=True)
    memory_key: str = "history"
    previous_history_template: str = DEFAULT_HISTORY_TEMPLATE
    split_chunk_size: int = 1000

    _memory_retriever: VectorStoreRetrieverMemory = PrivateAttr(default=None)
    _timestamps: List[datetime] = PrivateAttr(default_factory=list)

    @property
    def memory_retriever(self) -> VectorStoreRetrieverMemory:
        """Return a memory retriever from the passed retriever object."""
        if self._memory_retriever is not None:
            return self._memory_retriever
        self._memory_retriever = VectorStoreRetrieverMemory(retriever=self.retriever)
        return self._memory_retriever

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Return history and memory buffer."""
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                memory_variables = self.memory_retriever.load_memory_variables(inputs)
            previous_history = memory_variables[self.memory_retriever.memory_key]
        except AssertionError:  # happens when db is empty
            previous_history = ""
        current_history = super().load_memory_variables(inputs)
        template = SystemMessagePromptTemplate.from_template(
            self.previous_history_template
        )
        messages = [
            template.format(
                previous_history=previous_history,
                current_time=datetime.now().astimezone().strftime(TIMESTAMP_FORMAT),
            )
        ]
        messages.extend(current_history[self.memory_key])
        return {self.memory_key: messages}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save context from this conversation to buffer. Pruned."""
        BaseChatMemory.save_context(self, inputs, outputs)
        self._timestamps.append(datetime.now().astimezone())
        # Prune buffer if it exceeds max token limit
        buffer = self.chat_memory.messages
        curr_buffer_length = self.llm.get_num_tokens_from_messages(buffer)
        if curr_buffer_length > self.max_token_limit:
            while curr_buffer_length > self.max_token_limit:
                self._pop_and_store_interaction(buffer)
                curr_buffer_length = self.llm.get_num_tokens_from_messages(buffer)

    def save_remainder(self) -> None:
        """
        Save the remainder of the conversation buffer to the vector store.

        This is useful if you have made the vectorstore persistent, in which
        case this can be called before the end of the session to store the
        remainder of the conversation.
        """
        buffer = self.chat_memory.messages
        while len(buffer) > 0:
            self._pop_and_store_interaction(buffer)

    def _pop_and_store_interaction(self, buffer: List[BaseMessage]) -> None:
        input = buffer.pop(0)
        output = buffer.pop(0)
        timestamp = self._timestamps.pop(0).strftime(TIMESTAMP_FORMAT)
        # Split AI output into smaller chunks to avoid creating documents
        # that will overflow the context window
        ai_chunks = self._split_long_ai_text(str(output.content))
        for index, chunk in enumerate(ai_chunks):
            self.memory_retriever.save_context(
                {"Human": f"<{timestamp}/00> {str(input.content)}"},
                {"AI": f"<{timestamp}/{index:02}> {chunk}"},
            )

    def _split_long_ai_text(self, text: str) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(chunk_size=self.split_chunk_size)
        return [chunk.page_content for chunk in splitter.create_documents([text])]
