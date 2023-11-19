from typing import Dict, List

from langchain.agents.agent_toolkits.base import BaseToolkit
from langchain.tools import BaseTool
from langchain.tools.steam.prompt import (
    STEAM_GET_GAMES_DETAILS,
    STEAM_GET_GAMES_ID,
    STEAM_GET_RECOMMENDED_GAMES,
)
from langchain.tools.steam.tool import SteamWebAPIQueryRun
from langchain.utilities.steam import SteamWebAPIWrapper


class SteamToolkit(BaseToolkit):
    """Steam Toolkit."""

    tools: List[BaseTool] = []
    
    @classmethod
    def from_steam_api_wrapper(cls, steam_api_wrapper: SteamWebAPIWrapper) -> "SteamToolkit":
        operations: List[Dict] = [
            {
                "mode": "get_games_details",
                "name": "Get Games Details",
                "description": STEAM_GET_GAMES_DETAILS,
            },
            {
                "mode": "get_games_id",
                "name": "Get Games ID",
                "description": STEAM_GET_GAMES_ID,
            },
            {
                "mode": "get_recommended_games",
                "name": "Get Recommended Games",
                "description": STEAM_GET_RECOMMENDED_GAMES,
            },
        
        ]
        tools = [
            SteamWebAPIQueryRun(
                name=action["name"],
                description=action["description"],
                mode=action["mode"],
                api_wrapper=steam_api_wrapper,
            )
            for action in operations
        ]
        return cls(tools=tools)

    def get_tools(self) -> List[BaseTool]:
        """Get the tools in the toolkit."""
        return self.tools
