from abc import ABC, abstractmethod


class AnalysisProvider(ABC):
    @abstractmethod
    def analyze(self, resume_text: str) -> dict:
        pass

def match_job_description(self, resume_text: str, job_description_text: str) -> dict:
    raise NotImplementedError("Provider does not support job matching")
