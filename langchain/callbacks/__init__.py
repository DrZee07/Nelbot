"""Callback handlers that allow listening to events in LangChain."""
from langchain.callbacks.base import BaseCallbackManager
from langchain.callbacks.shared import SharedCallbackManager
from langchain.callbacks.stdout import StdOutCallbackHandler
from langchain.callbacks.tracers import SharedLangChainTracer


def get_callback_manager() -> BaseCallbackManager:
    """Return the shared callback manager."""
    return SharedCallbackManager()


def set_default_callback_manager() -> None:
    """Set default callback manager."""
    callback = get_callback_manager()
    callback.add_handler(StdOutCallbackHandler())


def set_tracing_callback_manager() -> None:
    """Set tracing callback manager."""
    callback = get_callback_manager()
    callback.add_handler(SharedLangChainTracer())
