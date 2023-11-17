from typing import Any, Dict, List, Optional, TYPE_CHECKING
from types import SimpleNamespace
from uuid import UUID

import functools
from langchain.callbacks.tracers.base import BaseTracer

from concurrent import futures

if TYPE_CHECKING:
    from langchain.callbacks.tracers.schemas import Run
    from comet_llm.chains.chain import Chain
    from comet_llm.experiment_info import ExperimentInfo
    from comet_llm import Span


def _get_run_type(run: "Run") -> str:
    if isinstance(run.run_type, str):
        return run.run_type
    elif hasattr(run.run_type, "value"):
        return run.run_type.value
    else:
        return str(run.run_type)

# @functools.lru_cache(maxsize=1)
# def _get_thread_executor():
#     return futures.ThreadPoolExecutor()


def import_comet_llm_api() -> SimpleNamespace:
    """Import comet_llm api and raise an error if it is not installed."""
    try:
        from comet_llm.chains import chain  # noqa: F401
        from comet_llm.chains import span  # noqa: F401
        from comet_llm.chains import api as chain_api  # noqa: F401
        from comet_llm import experiment_info  # noqa: F401

    except ImportError:
        raise ImportError(
            "To use the comet_ml callback manager you need to have the "
            "`comet_ml` python package installed. Please install it with"
            " `pip install comet_ml`"
        )
    return SimpleNamespace(
        chain=chain,
        span=span,
        chain_api=chain_api,
        experiment_info=experiment_info,
    )


class CometTracer(BaseTracer):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._span_map: Dict[UUID, "Span"] = {}
        self._chains_map: Dict[UUID, "Chain"] = {}
        self._initialize_comet_modules()
        #self._executor = _get_thread_executor()
        #self._futures = set()

    def _initialize_comet_modules(self) -> None:
        comet_llm_api = import_comet_llm_api()
        self._chain = comet_llm_api.chain
        self._span = comet_llm_api.span
        self._chain_api = comet_llm_api.chain_api
        self._experiment_info = comet_llm_api.experiment_info

    def _persist_run(self, run: "Run") -> None:
        chain_ = self._chains_map[run.id]
        chain_.set_outputs(outputs=run.outputs)
        #self._executor.submit(chain_api.log_chain, chain_)
        self._chain_api.log_chain(chain_)

    def _process_start_trace(self, run: "Run") -> None:
        if not run.parent_run_id:
            # This is the first run, which maps to a chain
            chain_: "Chain" = self._chain.Chain(
                inputs=run.inputs,
                metadata=None,
                experiment_info=self._experiment_info.get()
            )
            self._chains_map[run.id] = chain_
        else:
            span: "Span" = self._span.Span(
                inputs=run.inputs,
                category=_get_run_type(run),
                metadata=run.extra,
                name=run.name,
            )
            span.__api__start__(self._chains_map[run.parent_run_id])
            self._chains_map[run.id] = self._chains_map[run.parent_run_id]
            self._span_map[run.id] = span

    def _process_end_trace(self, run: "Run") -> None:
        if not run.parent_run_id:
            pass
            # Langchain will call _persist_run for us
        else:
            span = self._span_map[run.id]
            span.set_outputs(outputs=run.outputs)
            span.__api__end__()

    def _on_llm_start(self, run: "Run") -> None:
        """Process the LLM Run upon start."""
        self._process_start_trace(run)

    def _on_llm_end(self, run: "Run") -> None:
        """Process the LLM Run."""
        self._process_end_trace(run)

    def _on_llm_error(self, run: "Run") -> None:
        """Process the LLM Run upon error."""
        self._process_end_trace(run)

    def _on_chain_start(self, run: "Run") -> None:
        """Process the Chain Run upon start."""
        self._process_start_trace(run)

    def _on_chain_end(self, run: "Run") -> None:
        """Process the Chain Run."""
        self._process_end_trace(run)

    def _on_chain_error(self, run: "Run") -> None:
        """Process the Chain Run upon error."""
        self._process_end_trace(run)

    def _on_tool_start(self, run: "Run") -> None:
        """Process the Tool Run upon start."""
        self._process_start_trace(run)

    def _on_tool_end(self, run: "Run") -> None:
        """Process the Tool Run."""
        self._process_end_trace(run)

    def _on_tool_error(self, run: "Run") -> None:
        """Process the Tool Run upon error."""
        self._process_end_trace(run)