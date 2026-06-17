from providers.base import AnalysisProvider


class RuleBasedProvider(AnalysisProvider):
    provider_name = "rule-based"
    analysis_version = "rule-based-v1"

    def analyze(self, resume_text: str, target_career: dict) -> dict:
        words = resume_text.split()
        role_title = target_career.get("roleTitle", "Target Role")
        industry = target_career.get("industry", "Target Industry")

        return {
            "provider": self.provider_name,
            "model": "",
            "analysisVersion": "rule-based-target-career-v1",
            "score": min(100, max(40, len(words) // 8)),
            "wordCount": len(words),
            "roleFitSummary": f"Rule-based analysis for {role_title} in {industry}.",
            "dynamicScores": [
                {
                    "key": "roleAlignmentScore",
                    "label": "Role Alignment",
                    "score": 70,
                    "explanation": "Basic estimate of how clearly the resume aligns to the target role."
                },
                {
                    "key": "keywordCoverageScore",
                    "label": "Keyword Coverage",
                    "score": 65,
                    "explanation": "Basic estimate of target-role keyword coverage."
                },
                {
                    "key": "experienceRelevanceScore",
                    "label": "Experience Relevance",
                    "score": 65,
                    "explanation": "Basic estimate of whether the resume describes relevant experience."
                },
                {
                    "key": "resumeClarityScore",
                    "label": "Resume Clarity",
                    "score": 75,
                    "explanation": "Basic estimate of resume readability and structure."
                },
            ],
            "strengths": ["Resume was analyzed against the saved target career."],
            "recommendations": ["Use OpenAI analysis for role-specific scoring dimensions."],
            "roleSpecificGaps": [],
            "executiveSummary": f"This resume was evaluated for {role_title}.",
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

    def tailor_resume(self, resume_text: str, job_description_text: str) -> dict:
        return {
            "provider": self.provider_name,
            "model": "",
            "analysisVersion": "resume-tailoring-rule-based-v1",
            "tailoredExecutiveSummary": (
                "Senior engineering leader with experience across cloud architecture, "
                "software delivery, cybersecurity, and cross-functional technical leadership."
            ),
            "tailoredResumeBullets": [
                "Led cloud-focused engineering initiatives aligned to business, security, and delivery outcomes.",
                "Partnered with technical and non-technical stakeholders to deliver scalable software solutions.",
                "Improved engineering execution through architecture guidance, delivery practices, and team leadership.",
            ],
            "keywordsToAdd": [
                "cloud architecture",
                "stakeholder management",
                "technical leadership",
                "software delivery",
                "AWS",
            ],
            "rolePositioningAdvice": [
                "Add more measurable leadership scope, such as team size, budget, roadmap ownership, and business impact."
            ],
            "atsOptimizationAdvice": [
                "Mirror important job description keywords where they accurately reflect your experience."
            ],
            "rewriteWarnings": [
                "Rule-based tailoring is generic. Use OpenAI for stronger job-specific recommendations."
            ],
        }

    def prepare_interview(self, resume_text: str, job_description_text: str) -> dict:
        sample_question = {
            "question": "Tell me about a complex engineering initiative you led and the measurable outcome.",
            "answerFramework": [
                "Describe the business context.",
                "Explain your leadership role.",
                "Describe technical and delivery challenges.",
                "Share measurable outcomes."
            ],
            "followUpQuestions": [
                "How did you measure success?",
                "What would you do differently?"
            ]
        }

        return {
            "provider": self.provider_name,
            "model": "",
            "analysisVersion": "interview-prep-rule-based-v1",
            "behavioralQuestions": [sample_question],
            "leadershipQuestions": [sample_question],
            "systemDesignQuestions": [sample_question],
            "cloudArchitectureQuestions": [sample_question],
            "securityQuestions": [sample_question],
            "resumeSpecificQuestions": [sample_question],
            "jobSpecificQuestions": [sample_question],
            "interviewReadinessSummary": "Rule-based interview preparation generated. Use OpenAI for job-specific questions."
        }
