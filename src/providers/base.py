from abc import ABC, abstractmethod


class AnalysisProvider(ABC):
    @abstractmethod
    def analyze(self, resume_text: str) -> dict:
        pass
