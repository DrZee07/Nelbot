from importlib import metadata

from langchain_neo4j.graphs.neo4j_graph import Neo4jGraph
from langchain_neo4j.vectorstores.neo4j_vector import Neo4jVector

try:
    __version__ = metadata.version(__package__)
except metadata.PackageNotFoundError:
    # Case where package metadata is not available.
    __version__ = ""
del metadata  # optional, avoids polluting the results of dir(__package__)

__all__ = [
    "Neo4jVector",
    "Neo4jGraph",
    "__version__",
]
