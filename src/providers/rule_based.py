from providers.base import AnalysisProvider


class RuleBasedProvider(AnalysisProvider):
    provider_name = "rule-based"
    analysis_version = "rule-based-v1"

    def analyze(self, resume_text: str) -> dict:
        word_count = len(resume_text.split())

        strengths = [
            "Clear technical leadership foundation",
            "Relevant cloud and engineering management experience",
            "Strong fit for architecture-focused leadership roles",
        ]

        recommendations = [
            "Add measurable business outcomes using numbers, percentages, or dollar impact.",
            "Highlight leadership scope, including team size, delivery ownership, and stakeholder influence.",
            "Strengthen cloud architecture examples by naming AWS services, tradeoffs, and results.",
        ]

        score = min(95, max(60, 70 + min(word_count // 25, 20)))

        return {
            "provider": self.provider_name,
            "analysisVersion": self.analysis_version,
            "score": score,
            "wordCount": word_count,
            "strengths": strengths,
            "recommendations": recommendations,
        }
