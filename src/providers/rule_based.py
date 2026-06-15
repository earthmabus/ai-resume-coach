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

    def match_job_description(self, resume_text: str, job_description_text: str) -> dict:
        resume_words = set(resume_text.lower().replace(",", " ").replace(".", " ").split())
        jd_words = set(job_description_text.lower().replace(",", " ").replace(".", " ").split())

        common_words = resume_words.intersection(jd_words)
        missing_words = jd_words.difference(resume_words)

        important_missing = [
            word for word in missing_words
            if len(word) > 5
        ][:15]

        match_score = min(95, max(20, int((len(common_words) / max(len(jd_words), 1)) * 100)))

        return {
            "provider": self.provider_name,
            "model": "",
            "analysisVersion": "job-match-rule-based-v1",
            "matchScore": match_score,
            "leadershipMatchScore": match_score,
            "technicalMatchScore": match_score,
            "architectureMatchScore": match_score,
            "atsKeywordScore": match_score,
            "matchedKeywords": list(common_words)[:20],
            "missingKeywords": important_missing,
            "leadershipGaps": [
                "Add more explicit leadership scope, stakeholder influence, and measurable outcomes."
            ],
            "technicalGaps": [
                "Add more job-specific technologies, platforms, tools, and architecture keywords."
            ],
            "recommendedResumeChanges": [
                "Mirror important job description terminology where accurate.",
                "Add quantified accomplishments that align to the role.",
                "Strengthen leadership, architecture, delivery, and business impact examples."
            ],
            "executiveSummary": "Rule-based comparison completed. Use OpenAI provider for deeper semantic matching."
        }
