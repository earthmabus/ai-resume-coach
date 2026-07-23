import os

from providers.rule_based import RuleBasedProvider


def get_analysis_provider(provider_name=None):
    selected_provider = (provider_name or os.getenv("ANALYSIS_PROVIDER", "rule-based")).lower()

    if selected_provider == "rule-based":
        return RuleBasedProvider()

    if selected_provider == "openai":
        from providers.openai_provider import OpenAIProvider
        return OpenAIProvider()

    raise ValueError(f"Unsupported analysis provider: {selected_provider}")
