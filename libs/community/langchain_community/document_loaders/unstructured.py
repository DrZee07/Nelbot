"""Loader that uses unstructured to load files."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import IO, Any, Callable, Dict, Iterator, List, Optional, Sequence, Union, cast

from langchain_core.documents import Document

from langchain_community.document_loaders.base import BaseLoader


def satisfies_min_unstructured_version(min_version: str) -> bool:
    """Check if the installed `Unstructured` version exceeds the minimum version
    for the feature in question."""
    from unstructured.__version__ import __version__ as __unstructured_version__

    min_version_tuple = tuple([int(x) for x in min_version.split(".")])

    # NOTE(MthwRobinson) - enables the loader to work when you're using pre-release
    # versions of unstructured like 0.4.17-dev1
    _unstructured_version = __unstructured_version__.split("-")[0]
    unstructured_version_tuple = tuple(
        [int(x) for x in _unstructured_version.split(".")]
    )

    return unstructured_version_tuple >= min_version_tuple


def validate_unstructured_version(min_unstructured_version: str) -> None:
    """Raise an error if the `Unstructured` version does not exceed the
    specified minimum."""
    if not satisfies_min_unstructured_version(min_unstructured_version):
        raise ValueError(
            f"unstructured>={min_unstructured_version} is required in this loader."
        )


class UnstructuredBaseLoader(BaseLoader, ABC):
    """Base Loader that uses `Unstructured`."""

    def __init__(
        self,
        mode: str = "single",
        post_processors: Optional[List[Callable]] = None,
        **unstructured_kwargs: Any,
    ):
        """Initialize with file path."""
        _valid_modes = {"single", "elements", "paged"}

        if mode not in _valid_modes:
            raise ValueError(
                f"Got {mode} for `mode`, but should be one of `{_valid_modes}`"
            )
        
        self.mode = mode
        self.unstructured_kwargs = unstructured_kwargs
        self.post_processors = post_processors or []

    @abstractmethod
    def _get_elements(self) -> List:
        """Get elements."""

    @abstractmethod
    def _get_metadata(self) -> dict:
        """Get metadata."""

    def _post_process_elements(self, elements: list) -> list:
        """Applies post processing functions to extracted unstructured elements.
        Post processing functions are str -> str callables are passed
        in using the post_processors kwarg when the loader is instantiated."""
        for element in elements:
            for post_processor in self.post_processors:
                element.apply(post_processor)
        return elements

    def lazy_load(self) -> Iterator[Document]:
        """Load file."""
        elements = self._get_elements()
        self._post_process_elements(elements)
        if self.mode == "elements":
            for element in elements:
                metadata = self._get_metadata()
                # NOTE(MthwRobinson) - the attribute check is for backward compatibility
                # with unstructured<0.4.9. The metadata attributed was added in 0.4.9.
                if hasattr(element, "metadata"):
                    metadata.update(element.metadata.to_dict())
                if hasattr(element, "category"):
                    metadata["category"] = element.category
                yield Document(page_content=str(element), metadata=metadata)
        elif self.mode == "paged":
            text_dict: Dict[int, str] = {}
            meta_dict: Dict[int, Dict] = {}

            for idx, element in enumerate(elements):
                metadata = self._get_metadata()
                if hasattr(element, "metadata"):
                    metadata.update(element.metadata.to_dict())
                page_number = metadata.get("page_number", 1)

                # Check if this page_number already exists in docs_dict
                if page_number not in text_dict:
                    # If not, create new entry with initial text and metadata
                    text_dict[page_number] = str(element) + "\n\n"
                    meta_dict[page_number] = metadata
                else:
                    # If exists, append to text and update the metadata
                    text_dict[page_number] += str(element) + "\n\n"
                    meta_dict[page_number].update(metadata)

            # Convert the dict to a list of Document objects
            for key in text_dict.keys():
                yield Document(page_content=text_dict[key], metadata=meta_dict[key])
        elif self.mode == "single":
            metadata = self._get_metadata()
            text = "\n\n".join([str(el) for el in elements])
            yield Document(page_content=text, metadata=metadata)
        else:
            raise ValueError(f"mode of {self.mode} not supported.")


class UnstructuredFileLoader(UnstructuredBaseLoader):
    """Load files using `Unstructured`.

    The file loader uses the
    unstructured partition function and will automatically detect the file
    type. You can run the loader in one of two modes: "single" and "elements".
    If you use "single" mode, the document will be returned as a single
    langchain Document object. If you use "elements" mode, the unstructured
    library will split the document into elements such as Title and NarrativeText.
    You can pass in additional unstructured kwargs after mode to apply
    different unstructured settings.

    Examples
    --------
    from langchain_community.document_loaders import UnstructuredFileLoader

    loader = UnstructuredFileLoader(
        "example.pdf", mode="elements", strategy="fast",
    )
    docs = loader.load()

    References
    ----------
    https://unstructured-io.github.io/unstructured/bricks.html#partition
    """

    def __init__(
        self,
        file_path: Union[str, List[str], Path, List[Path], None],
        mode: str = "single",
        **unstructured_kwargs: Any,
    ):
        """Initialize with file path."""
        self.file_path = file_path

        try:
            import unstructured  # noqa:F401
        except ImportError:
            raise ImportError(
                "unstructured package not found, please install it with "
                "`pip install unstructured`"
            )
        
        if not satisfies_min_unstructured_version("0.5.4"):
            if "strategy" in unstructured_kwargs:
                unstructured_kwargs.pop("strategy")

        super().__init__(mode=mode, **unstructured_kwargs)

    def _get_elements(self) -> List:
        from unstructured.partition.auto import partition

        if isinstance(self.file_path, list):
            elements = []
            for file in self.file_path:
                if isinstance(file, Path):
                    file = str(file)
                elements.extend(partition(filename=file, **self.unstructured_kwargs))
            return elements
        else:
            if isinstance(self.file_path, Path):
                self.file_path = str(self.file_path)
            return partition(filename=self.file_path, **self.unstructured_kwargs)

    def _get_metadata(self) -> dict:
        return {"source": self.file_path}


def get_elements_from_api(
    file_path: Union[str, Path, None] = None,
    file: Union[IO, None] = None,
    api_url: str = "https://api.unstructured.io/general/v0/general",
    api_key: str = "",
    **unstructured_kwargs: Any,
) -> List:
    """Retrieve a list of elements from the `Unstructured API`."""

    try:
        import unstructured_client  # noqa:F401
        from unstructured.staging.base import elements_from_json  # noqa:F401
    except ImportError:
        raise ImportError(
            "unstructured_client and/or unstructured package not found, please install it with "
            "`pip install unstructured-client` or `pip install unstructured`."
        )
    from unstructured.staging.base import elements_from_json
    from unstructured_client.models import operations, shared

    content = None
    if file is not None:            
        content = file.read()
    if content is None and file_path is not None:
        with open(file_path, 'rb') as f:
            content = f.read()
    if content is None:
        raise ValueError("Either file or file_path must be provided")

    client = unstructured_client.UnstructuredClient(api_key_auth=api_key, server_url=api_url)
    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=shared.Files(
                content=content,
                file_name=str(file_path)
            ),
            **unstructured_kwargs,
        ),
    )
    response = client.general.partition(req)

    if response.status_code == 200:
        return elements_from_json(text=response.raw_response.text)
    else:
        raise ValueError(
            f"Receive unexpected status code {response.status_code} from the API.",
        )


class UnstructuredAPIFileLoader(UnstructuredBaseLoader):
    """Load files using `Unstructured` API.

    By default, the loader makes a call to the hosted Unstructured API.
    If you are running the unstructured API locally, you can change the
    API rule by passing in the url parameter when you initialize the loader.
    The hosted Unstructured API requires an API key. See
    https://www.unstructured.io/api-key/ if you need to generate a key.

    You can run the loader in one of two modes: "single" and "elements".
    If you use "single" mode, the document will be returned as a single
    langchain Document object. If you use "elements" mode, the unstructured
    library will split the document into elements such as Title and NarrativeText.
    You can pass in additional unstructured kwargs after mode to apply
    different unstructured settings.

    Examples
    ```python
    from langchain_community.document_loaders import UnstructuredAPIFileLoader

    loader = UnstructuredFileAPILoader(
        "example.pdf", mode="elements", strategy="fast", api_key="MY_API_KEY",
    )
    docs = loader.load()

    References
    ----------
    https://unstructured-io.github.io/unstructured/bricks.html#partition
    https://www.unstructured.io/api-key/
    https://github.com/Unstructured-IO/unstructured-api
    """

    def __init__(
        self,
        file_path: Union[str, List[str], None] = "",
        mode: str = "single",
        url: str = "https://api.unstructured.io/general/v0/general",
        api_key: str = "",
        **unstructured_kwargs: Any,
    ):
        """Initialize with file path."""

        self.file_path = file_path
        self.url = url
        self.api_key = api_key

        super().__init__(mode=mode, **unstructured_kwargs)

    def _get_metadata(self) -> dict:
        return {"source": self.file_path}

    def _get_elements(self) -> List:
        if isinstance(self.file_path, List):
            elements = []
            for path in self.file_path:
                elements.extend(
                    get_elements_from_api(
                        file_path=path,
                        api_key=self.api_key,
                        api_url=self.url,
                        **self.unstructured_kwargs,
                    )
                )
            return elements

        return get_elements_from_api(
            file_path=self.file_path,
            api_key=self.api_key,
            api_url=self.url,
            **self.unstructured_kwargs,
        )


class UnstructuredFileIOLoader(UnstructuredBaseLoader):
    """Load files using `Unstructured`.

    The file loader
    uses the unstructured partition function and will automatically detect the file
    type. You can run the loader in one of two modes: "single" and "elements".
    If you use "single" mode, the document will be returned as a single
    langchain Document object. If you use "elements" mode, the unstructured
    library will split the document into elements such as Title and NarrativeText.
    You can pass in additional unstructured kwargs after mode to apply
    different unstructured settings.

    Examples
    --------
    from langchain_community.document_loaders import UnstructuredFileIOLoader

    with open("example.pdf", "rb") as f:
        loader = UnstructuredFileIOLoader(
            f, mode="elements", strategy="fast",
        )
        docs = loader.load()


    References
    ----------
    https://unstructured-io.github.io/unstructured/bricks.html#partition
    """

    def __init__(
        self,
        file: IO[bytes],
        mode: str = "single",
        **unstructured_kwargs: Any,
    ):
        """Initialize with file path."""
        self.file = file

        try:
            import unstructured  # noqa:F401
        except ImportError:
            raise ImportError(
                "unstructured package not found, please install it with "
                "`pip install unstructured`"
            )
        
        if not satisfies_min_unstructured_version("0.5.4"):
            if "strategy" in unstructured_kwargs:
                unstructured_kwargs.pop("strategy")
                
        super().__init__(mode=mode, **unstructured_kwargs)

    def _get_elements(self) -> List:
        from unstructured.partition.auto import partition

        return partition(file=self.file, **self.unstructured_kwargs)

    def _get_metadata(self) -> dict:
        return {}


class UnstructuredAPIFileIOLoader(UnstructuredBaseLoader):
    """Load files using `Unstructured` API.

    By default, the loader makes a call to the hosted Unstructured API.
    If you are running the unstructured API locally, you can change the
    API rule by passing in the url parameter when you initialize the loader.
    The hosted Unstructured API requires an API key. See
    https://www.unstructured.io/api-key/ if you need to generate a key.

    You can run the loader in one of two modes: "single" and "elements".
    If you use "single" mode, the document will be returned as a single
    langchain Document object. If you use "elements" mode, the unstructured
    library will split the document into elements such as Title and NarrativeText.
    You can pass in additional unstructured kwargs after mode to apply
    different unstructured settings.

    Examples
    --------
    from langchain_community.document_loaders import UnstructuredAPIFileLoader

    with open("example.pdf", "rb") as f:
        loader = UnstructuredFileAPILoader(
            f, mode="elements", strategy="fast", api_key="MY_API_KEY",
        )
        docs = loader.load()

    References
    ----------
    https://unstructured-io.github.io/unstructured/bricks.html#partition
    https://www.unstructured.io/api-key/
    https://github.com/Unstructured-IO/unstructured-api
    """

    def __init__(
        self,
        file: Union[IO, Sequence[IO]],
        mode: str = "single",
        url: str = "https://api.unstructured.io/general/v0/general",
        api_key: str = "",
        **unstructured_kwargs: Any,
    ):
        """Initialize with file path."""
        
        self.file = file
        self.url = url
        self.api_key = api_key

        super().__init__(mode=mode, **unstructured_kwargs)

    def _get_elements(self) -> List:
        if isinstance(self.file, Sequence):
            if _metadata_filenames := self.unstructured_kwargs.pop("metadata_filename"):
                elements = []
                for i, file in enumerate(self.file):
                    elements.extend(
                        get_elements_from_api(
                            file=file,
                            file_path=_metadata_filenames[i],
                            api_key=self.api_key,
                            api_url=self.url,
                            **self.unstructured_kwargs,
                        )
                    )
                return elements
            else:
                raise ValueError(
                    "If partitioning a file via api,"
                    " metadata_filename must be specified as well.",
                )


        return get_elements_from_api(
            file=self.file,
            file_path=self.unstructured_kwargs.pop("metadata_filename"),
            api_key=self.api_key,
            api_url=self.url,
            **self.unstructured_kwargs,
        )
    
    def _get_metadata(self) -> dict:
        return {}
