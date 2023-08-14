from typing import Any, Dict, Optional

from langchainhub import Client

from langchain.load.dump import dumps
from langchain.load.load import loads
from langchain.utils import get_from_dict_or_env, get_from_env


def _get_client(kwargs: Dict[str, Any]) -> Client:
    api_url = get_from_dict_or_env(kwargs, "api_url", "LANGCHAIN_HUB_API_URL")

    # read hub-specific api key
    api_key = get_from_dict_or_env(kwargs, "api_key", "LANGCHAIN_HUB_API_KEY", None)

    # use default api key as fallback
    if api_key is None:
        api_key = get_from_env("api_key", "LANGCHAIN_API_KEY")
    return Client(api_url, api_key=api_key)


def push(
    repo_full_name: str,
    parent_commit_hash: Optional[str],
    object: Any,
    **kwargs: Dict[str, Any]
) -> str:
    """
    Pushes an object to the hub and returns the URL.
    """
    client = _get_client(kwargs)
    manifest_json = dumps(object)
    resp = client.push(repo_full_name, parent_commit_hash, manifest_json)
    commit_hash: str = resp["commit"]["commit_hash"]
    return commit_hash


def pull(repo_full_name: str, commit_hash: str, **kwargs: Dict[str, Any]) -> Any:
    """
    Pulls an object from the hub and returns it.
    """
    client = _get_client(kwargs)
    resp: str = client.pull(repo_full_name, commit_hash)
    return loads(resp)
