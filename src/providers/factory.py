import os

from providers.rule_based import RuleBasedProvider


def get_analysis_provider():
    provider_name = os.getenv("ANALYSIS_PROVIDER", "rule-based").lower()

    if provider_name == "rule-based":
        return RuleBasedProvider()

    raise ValueError(f"Unsupported analysis provider: {provider_name}")
