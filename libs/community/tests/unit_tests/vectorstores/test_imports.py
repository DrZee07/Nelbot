from langchain_core.vectorstores import VectorStore

from langchain_community import vectorstores
from langchain_community.vectorstores import __all__, _module_lookup

EXPECTED_ALL = [
    "Aerospike",
    "AlibabaCloudOpenSearch",
    "AlibabaCloudOpenSearchSettings",
    "AnalyticDB",
    "Annoy",
    "ApacheDoris",
    "AstraDB",
    "AtlasDB",
    "AwaDB",
    "AzureCosmosDBVectorSearch",
    "AzureSearch",
    "BESVectorStore",
    "Bagel",
    "BaiduVectorDB",
    "BigQueryVectorSearch",
    "Cassandra",
    "Chroma",
    "Clarifai",
    "Clickhouse",
    "ClickhouseSettings",
    "CouchbaseVectorStore",
    "DashVector",
    "DatabricksVectorSearch",
    "DeepLake",
    "Dingo",
    "DistanceStrategy",
    "DocArrayHnswSearch",
    "DocArrayInMemorySearch",
    "DocumentDBVectorSearch",
    "DuckDB",
    "EcloudESVectorStore",
    "ElasticKnnSearch",
    "ElasticVectorSearch",
    "ElasticsearchStore",
    "Epsilla",
    "FAISS",
    "HanaDB",
    "Hologres",
    "InMemoryVectorStore",
    "InfinispanVS",
    "KDBAI",
    "Kinetica",
    "KineticaSettings",
    "LLMRails",
    "LanceDB",
    "Lantern",
    "ManticoreSearch",
    "ManticoreSearchSettings",
    "Marqo",
    "MatchingEngine",
    "Meilisearch",
    "Milvus",
    "MomentoVectorIndex",
    "MongoDBAtlasVectorSearch",
    "MyScale",
    "MyScaleSettings",
    "Neo4jVector",
    "NeuralDBClientVectorStore",
    "NeuralDBVectorStore",
    "OpenSearchVectorSearch",
    "OracleVS",
    "PGEmbedding",
    "PGVector",
    "PathwayVectorClient",
    "Pinecone",
    "Qdrant",
    "Redis",
    "Relyt",
    "Rockset",
    "SKLearnVectorStore",
    "SQLiteVSS",
    "ScaNN",
    "SemaDB",
    "SingleStoreDB",
    "StarRocks",
    "SupabaseVectorStore",
    "SurrealDBStore",
    "Tair",
    "TencentVectorDB",
    "TiDBVectorStore",
    "Tigris",
    "TileDB",
    "TimescaleVector",
    "Typesense",
    "UpstashVectorStore",
    "USearch",
    "VDMS",
    "Vald",
    "Vearch",
    "Vectara",
    "VectorStore",
    "VespaStore",
    "VLite",
    "Weaviate",
    "Yellowbrick",
    "ZepVectorStore",
    "ZepCloudVectorStore",
    "Zilliz",
]


def test_all_imports_exclusive() -> None:
    """Simple test to make sure all things can be imported."""
    for cls in vectorstores.__all__:
        if cls not in [
            "AlibabaCloudOpenSearchSettings",
            "ClickhouseSettings",
            "MyScaleSettings",
            "PathwayVectorClient",
            "DistanceStrategy",
            "KineticaSettings",
            "ManticoreSearchSettings",
        ]:
            assert issubclass(getattr(vectorstores, cls), VectorStore)


def test_all_imports() -> None:
    assert set(__all__) == set(EXPECTED_ALL)
    assert set(__all__) == set(_module_lookup.keys())
