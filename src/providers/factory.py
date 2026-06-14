import os

from providers.rule_based import RuleBasedProvider
from providers.openai_provider import OpenAIProvider


def get_analysis_provider():
    provider_name = os.getenv("ANALYSIS_PROVIDER", "rule-based").lower()

    if provider_name == "rule-based":
        return RuleBasedProvider()

    if provider_name == "openai":
        return OpenAIProvider()

    raise ValueError(f"Unsupported analysis provider: {provider_name}")
