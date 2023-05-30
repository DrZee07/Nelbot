from typing import List, Optional

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader


class BigQueryLoader(BaseLoader):
    """Loads a query result from BigQuery into a list of documents.

    Each document represents one row of the result. The `page_content_columns`
    are written into the `page_content` of the document. The `metadata_columns`
    are written into the `metadata` of the document. By default, all columns
    are written into the `page_content` and none into the `metadata`.

    """

    def __init__(
            self,
            query: str,
            project: Optional[str] = None,
            page_content_columns: Optional[List[str]] = None,
            metadata_columns: Optional[List[str]] = None,
            credentials=None,
    ):
        """
        :param query: The query to run in BigQuery.
        :param project: Optional. The project to run the query in.
        :param page_content_columns: Optional. The columns to write into the `page_content` of the document.
        :param metadata_columns: Optional. The columns to write into the `metadata` of the document.
        :param credentials : google.auth.credentials.Credentials, optional
            Credentials for accessing Google APIs. Use this parameter to override
            default credentials, such as to use Compute Engine
            :class:`google.auth.compute_engine.Credentials` or Service Account
            :class:`google.oauth2.service_account.Credentials` directly.
        """
        self.query = query
        self.project = project
        self.page_content_columns = page_content_columns
        self.metadata_columns = metadata_columns
        self.credentials = credentials

    def load(self) -> List[Document]:
        try:
            from google.cloud import bigquery
        except ImportError as ex:
            raise ValueError(
                "Could not import google-cloud-bigquery python package. "
                "Please install it with `pip install google-cloud-bigquery`."
            ) from ex

        bq_client = bigquery.Client(credentials=self.credentials, project=self.project)
        query_result = bq_client.query(self.query).result()
        docs: List[Document] = []

        page_content_columns = self.page_content_columns
        metadata_columns = self.metadata_columns

        if page_content_columns is None:
            page_content_columns = [column.name for column in query_result.schema]
        if metadata_columns is None:
            metadata_columns = []

        for row in query_result:
            page_content = "\n".join(
                f"{k}: {v}" for k, v in row.items() if k in page_content_columns
            )
            metadata = {k: v for k, v in row.items() if k in metadata_columns}
            doc = Document(page_content=page_content, metadata=metadata)
            docs.append(doc)

        return docs
