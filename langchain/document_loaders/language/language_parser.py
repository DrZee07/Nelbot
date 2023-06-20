from typing import List
from abc import ABC, abstractmethod


class LanguageParser(ABC):
    def __init__(self, code: str):
        self.code = code

    def is_valid(self) -> bool:
        return True

    @abstractmethod
    def simplify_code(self) -> List[str]:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def extract_functions_classes(self) -> str:
        raise NotImplementedError  # pragma: no cover
