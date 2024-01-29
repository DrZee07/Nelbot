import importlib.util
from typing import Any, Dict, List, Optional
import spacy

from langchain_core.embeddings import Embeddings
from langchain_core.pydantic_v1 import BaseModel, Extra, root_validator


class SpacyEmbeddings(BaseModel, Embeddings):
    """Embeddings by spaCy models.

    Attributes:
        nlp (str): Name of a spaCy model.
        nlp_model (Any): The spaCy model loaded into memory.

    Methods:
        embed_documents(texts: List[str]) -> List[List[float]]:
            Generates embeddings for a list of documents.
        embed_query(text: str) -> List[float]:
            Generates an embedding for a single piece of text.
    """

    nlp: str = "en_core_web_sm"
    nlp_model: Optional[Any] = None
    

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid  # Forbid extra attributes during model initialization

    @root_validator(pre=True)
    def validate_environment(cls, values: Dict) -> Dict:
        """
        Validates that the spaCy package and the model are installed.

        Args:
            values (Dict): The values provided to the class constructor.

        Returns:
            The validated values.

        Raises:
            ValueError: If the spaCy package or the
            model are not installed.
        """
        if values.get("nlp") is None:
            values["nlp"] = "en_core_web_sm"

        nlp = values.get("nlp")


        # Check if the spaCy package is installed
        if importlib.util.find_spec("spacy") is None:
            raise ValueError(
                "SpaCy package not found. "
                "Please install it with `pip install spacy`."
            )
        try:
            # Try to load the spaCy model


            values["nlp_model"] = spacy.load(nlp)
        except OSError:
            # If the model is not found, raise a ValueError
            raise ValueError(
                f"SpaCy model '{nlp}' not found. "
                f"Please install it with"
                f" `python -m spacy download {nlp}`"
                "or provide a valid spaCy model name."
            )
        return values  # Return the validated values

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a list of documents.

        Args:
            texts (List[str]): The documents to generate embeddings for.

        Returns:
            A list of embeddings, one for each document.
        """
        return [self.nlp_model(text).vector.tolist() for text in texts]

    def embed_query(self, text: str) -> List[float]:
        """
        Generates an embedding for a single piece of text.

        Args:
            text (str): The text to generate an embedding for.

        Returns:
            The embedding for the text.
        """
        return self.nlp_model(text).vector.tolist()

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Asynchronously generates embeddings for a list of documents.
        This method is not implemented and raises a NotImplementedError.

        Args:
            texts (List[str]): The documents to generate embeddings for.

        Raises:
            NotImplementedError: This method is not implemented.
        """
        raise NotImplementedError("Asynchronous embedding generation is not supported.")

    async def aembed_query(self, text: str) -> List[float]:
        """
        Asynchronously generates an embedding for a single piece of text.
        This method is not implemented and raises a NotImplementedError.

        Args:
            text (str): The text to generate an embedding for.

        Raises:
            NotImplementedError: This method is not implemented.
        """
        raise NotImplementedError("Asynchronous embedding generation is not supported.")
