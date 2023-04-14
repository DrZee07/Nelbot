"""Loader that uses Diffbot to load webpages in text format."""
import logging
import requests
from typing import Any, List

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader


logger = logging.getLogger(__file__)


class DiffbotLoader(BaseLoader):
    """Loader that loads Diffbot file json."""

    def __init__(self, access_token: str, urls: List[str], continue_on_failure: bool = True):
        """Initialize with access token, ids, and key."""
        self.access_token = access_token        
        self.urls = urls
        self.continue_on_failure = continue_on_failure

    def _diffbot_api_url(self, diffbot_api: str) -> str:
        return f"https://api.diffbot.com/v3/{diffbot_api}"

    def _get_diffbot_data(self, url: str) -> Any:
        """Get Diffbot file from Diffbot REST API."""
        # TODO: Add support for other Diffbot APIs
        diffbot_url = self._diffbot_api_url("article")
        params = {
            "token": self.access_token,
            "url": url,
        }
        response = requests.get(diffbot_url, params=params, timeout=10)

        # TODO: handle non-ok errors
        return response.json() if response.ok else {}

    def load(self) -> List[Document]:
        """Extract text from Diffbot on all the URLs and return Document instances"""
        docs: List[Document] = list()

        for url in self.urls:
            try:
                data = self._get_diffbot_data(url)
                text = data["objects"][0]["text"] if "objects" in data else ""
                metadata = {"source": url}
                docs.append(Document(page_content=text, metadata=metadata))
            except Exception as e:
                if self.continue_on_failure:
                    logger.error(f"Error fetching or processing {url}, exception: {e}")
                else:
                    raise e
        return docs