from typing import Optional
import json

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools.imdb.base import IMDbBaseTool


class IMDbSearchMovieKeyword(IMDbBaseTool):
    """Tool that searches movies with key word"""

    name: str = "imdb_search_movie_keyword"
    description: str = (
        "Searches IMDb for a movie with the given key word returns a "
        "JSON array containing the search results, sorted by relevance. "
        "Each entry in the array contains the movie title and its ID."
    )

    def _run(
        self,
        keyword: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Searches IMDB for a movie that match a given keyword
            returns a JSON array containing the search results, sorted by relevance.
            Each entry in the array contains the movie title and its ID.
        """
        m = self.client.get_keyword(keyword)
        movies = list(map(
            lambda m: {'title': m.get('title'), 'id': m.getID()},
            m[:3]
        ))
        return json.dumps(movies)
