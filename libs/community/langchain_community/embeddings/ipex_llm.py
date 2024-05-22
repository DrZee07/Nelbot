# This file is adapted from
# https://github.com/langchain-ai/langchain/blob/master/libs/community/langchain_community/embeddings/huggingface.py

import logging
from typing import Any, Dict, List, Optional

from ipex_llm.transformers.convert import _optimize_post, _optimize_pre
from langchain_core.embeddings import Embeddings
from langchain_core.pydantic_v1 import BaseModel, Extra, Field

DEFAULT_BGE_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_QUERY_BGE_INSTRUCTION_EN = (
    "Represent this question for searching relevant passages: "
)
DEFAULT_QUERY_BGE_INSTRUCTION_ZH = "为这个句子生成表示以用于检索相关文章："
logger = logging.getLogger(__name__)

class IpexLLMBgeEmbeddings(BaseModel, Embeddings):
    """Wrapper around the BGE embedding model
    with IPEX-LLM optimizations on Intel CPUs and GPUs.

    To use, you should have the ``ipex-llm``
    and ``sentence_transformers`` package installed. Refer to
    `here <https://python.langchain.com/v0.1/docs/integrations/text_embedding/ipex_llm/>`_
    for installation on Intel CPU.

    Example on Intel CPU:
        .. code-block:: python

            from langchain_community.embeddings import IpexLLMBgeEmbeddings

            embedding_model = IpexLLMBgeEmbeddings(
                model_name="BAAI/bge-large-en-v1.5",
                model_kwargs={},
                encode_kwargs={"normalize_embeddings": True},
            )

    Refer to
    `here <https://python.langchain.com/v0.1/docs/integrations/text_embedding/ipex_llm_gpu/>`_
    for installation on Intel GPU.

    Example on Intel GPU:
        .. code-block:: python

            from langchain_community.embeddings import IpexLLMBgeEmbeddings

            embedding_model = IpexLLMBgeEmbeddings(
                model_name="BAAI/bge-large-en-v1.5",
                model_kwargs={"device": "xpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
    """

    client: Any  #: :meta private:
    model_name: str = DEFAULT_BGE_MODEL
    """Model name to use."""
    cache_folder: Optional[str] = None
    """Path to store models.
    Can be also set by SENTENCE_TRANSFORMERS_HOME environment variable."""
    model_kwargs: Dict[str, Any] = Field(default_factory=dict)
    """Keyword arguments to pass to the model."""
    encode_kwargs: Dict[str, Any] = Field(default_factory=dict)
    """Keyword arguments to pass when calling the `encode` method of the model."""
    query_instruction: str = DEFAULT_QUERY_BGE_INSTRUCTION_EN
    """Instruction to use for embedding query."""
    embed_instruction: str = ""
    """Instruction to use for embedding document."""

    def __init__(self, **kwargs: Any):
        """Initialize the sentence_transformer."""
        super().__init__(**kwargs)
        try:
            import sentence_transformers

        except ImportError as exc:
            raise ImportError(
                "Could not import sentence_transformers python package. "
                "Please install it with `pip install sentence_transformers`."
            ) from exc

        # Set "cpu" as default device
        if "device" not in self.model_kwargs:
            self.model_kwargs["device"] = "cpu"

        if self.model_kwargs["device"] not in ["cpu", "xpu"]:
            logger.warning(
                "IpexLLMBgeEmbeddings currently only supports device to be "
                f"'cpu' or 'xpu', but you have: {self.model_kwargs["device"]};"
                " Use 'cpu' instead."
            )
            self.model_kwargs["device"] = "cpu"

        self.client = sentence_transformers.SentenceTransformer(
            self.model_name, cache_folder=self.cache_folder, **self.model_kwargs
        )

        # Add ipex-llm optimizations
        self.client = _optimize_pre(self.client)
        self.client = _optimize_post(self.client)
        if self.model_kwargs["device"] == "xpu":
            self.client = self.client.half().to('xpu')

        if "-zh" in self.model_name:
            self.query_instruction = DEFAULT_QUERY_BGE_INSTRUCTION_ZH

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compute doc embeddings using a HuggingFace transformer model.

        Args:
            texts: The list of texts to embed.

        Returns:
            List of embeddings, one for each text.
        """
        texts = [self.embed_instruction + t.replace("\n", " ") for t in texts]
        embeddings = self.client.encode(texts, **self.encode_kwargs)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """Compute query embeddings using a HuggingFace transformer model.

        Args:
            text: The text to embed.

        Returns:
            Embeddings for the text.
        """
        text = text.replace("\n", " ")
        embedding = self.client.encode(
            self.query_instruction + text, **self.encode_kwargs
        )
        return embedding.tolist()
