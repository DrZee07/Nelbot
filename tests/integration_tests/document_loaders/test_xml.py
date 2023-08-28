import os
from pathlib import Path

from langchain_xfyun.document_loaders import UnstructuredXMLLoader

EXAMPLE_DIRECTORY = file_path = Path(__file__).parent.parent / "examples"


def test_unstructured_xml_loader() -> None:
    """Test unstructured loader."""
    file_path = os.path.join(EXAMPLE_DIRECTORY, "factbook.xml")
    loader = UnstructuredXMLLoader(str(file_path))
    docs = loader.load()

    assert len(docs) == 1
