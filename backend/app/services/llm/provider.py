from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LLMProvider(ABC):
    @abstractmethod
    def generate_response(self, system_instruction: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a response given a system instruction and a list of message dicts.
        messages should be of the format:
        [{"role": "user"|"assistant", "content": "hello", "name": "optional_name"}]
        """
        pass
