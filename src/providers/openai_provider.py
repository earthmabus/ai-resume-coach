import json
import os

from openai import OpenAI

from providers.base import AnalysisProvider


class OpenAIProvider(AnalysisProvider):
    provider_name = "openai"

    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.5")
        self.analysis_version = f"openai-{self.model}-v1"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def analyze(self, resume_text: str, target_career: dict) -> dict:
        role_title = target_career.get("roleTitle", "")
        industry = target_career.get("industry", "")

        prompt = f"""
You are an expert resume coach.

The user is targeting this career:

Role Title: {role_title}
Industry: {industry}
Seniority Level: {target_career.get("seniorityLevel", "")}
Work Environment: {target_career.get("workEnvironment", "")}
Key Responsibilities: {target_career.get("keyResponsibilities", "")}
Required Skills: {target_career.get("requiredSkills", "")}
Certifications / Licenses: {target_career.get("certifications", "")}
Physical Requirements: {target_career.get("physicalRequirements", "")}
Technical Requirements: {target_career.get("technicalRequirements", "")}
Leadership Requirements: {target_career.get("leadershipRequirements", "")}
Career Goal Summary: {target_career.get("careerGoalSummary", "")}

Analyze the resume for fit against this target career.

You must create the most appropriate scoring dimensions for this role.
Do not always use software engineering, architecture, technical, or leadership dimensions.
For example:
- Waste disposal roles may need physical ability, safety compliance, reliability, equipment operation, and route efficiency.
- Nursing roles may need patient care, clinical judgment, certifications, documentation, and care coordination.
- Software leadership roles may need engineering leadership, architecture judgment, delivery ownership, cloud strategy, and stakeholder influence.

Return only valid JSON with this exact shape:

{{
  "score": 0,
  "wordCount": 0,
  "roleFitSummary": "string",
  "dynamicScores": [
    {{
      "key": "camelCaseScoreName",
      "label": "Human readable score name",
      "score": 0,
      "explanation": "Why this score was assigned"
    }}
  ],
  "strengths": ["string"],
  "recommendations": ["string"],
  "roleSpecificGaps": ["string"],
  "executiveSummary": "string"
}}

Rules:
- Overall score must be 0-100.
- Each dynamic score must be 0-100.
- Generate 4 to 7 dynamic score dimensions.
- Dimensions must fit the target role and industry.
- Do not invent experience not shown in the resume.
- Prefer practical hiring-manager-relevant criteria.
- Use concise explanations.

Resume:
\"\"\"
{resume_text[:12000]}
\"\"\"
"""

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        parsed = self._parse_json_response(response)

        return {
            "provider": self.provider_name,
            "model": self.model,
            "analysisVersion": f"{self.provider_name}-{self.model}-target-career-v1",
            "score": parsed.get("score", 0),
            "wordCount": parsed.get("wordCount", len(resume_text.split())),
            "roleFitSummary": parsed.get("roleFitSummary", ""),
            "dynamicScores": parsed.get("dynamicScores", []),
            "strengths": parsed.get("strengths", []),
            "recommendations": parsed.get("recommendations", []),
            "roleSpecificGaps": parsed.get("roleSpecificGaps", []),
            "executiveSummary": parsed.get("executiveSummary", ""),
        }

    def match_job_description(self, resume_text: str, job_description_text: str) -> dict:
        prompt = f"""
You are an expert career coach for senior software engineering managers, cloud architects, and director-level engineering candidates.

Compare the resume against the job description.

Return only valid JSON with this exact shape:

{{
  "matchScore": 0,
  "leadershipMatchScore": 0,
  "technicalMatchScore": 0,
  "architectureMatchScore": 0,
  "atsKeywordScore": 0,
  "matchedKeywords": ["string"],
  "missingKeywords": ["string"],
  "leadershipGaps": ["string"],
  "technicalGaps": ["string"],
  "recommendedResumeChanges": ["string"],
  "executiveSummary": "string"
}}

Resume:
\"\"\"
{resume_text[:8000]}
\"\"\"

Job Description:
\"\"\"
{job_description_text[:8000]}
\"\"\"
"""

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            text={
                "format": {
                    "type": "json_object"
                }
            },
        )

        parsed = json.loads(response.output_text)

        return {
            "provider": self.provider_name,
            "model": self.model,
            "analysisVersion": f"job-match-{self.model}-v1",
            "matchScore": int(parsed.get("matchScore", 0)),
            "leadershipMatchScore": int(parsed.get("leadershipMatchScore", 0)),
            "technicalMatchScore": int(parsed.get("technicalMatchScore", 0)),
            "architectureMatchScore": int(parsed.get("architectureMatchScore", 0)),
            "atsKeywordScore": int(parsed.get("atsKeywordScore", 0)),
            "matchedKeywords": parsed.get("matchedKeywords", []),
            "missingKeywords": parsed.get("missingKeywords", []),
            "leadershipGaps": parsed.get("leadershipGaps", []),
            "technicalGaps": parsed.get("technicalGaps", []),
            "recommendedResumeChanges": parsed.get("recommendedResumeChanges", []),
            "executiveSummary": parsed.get("executiveSummary", ""),
        }

    def tailor_resume(self, resume_text: str, job_description_text: str) -> dict:
        prompt = f"""
You are an expert resume strategist for senior software engineering managers, cloud architects, and director-level engineering candidates.

Using the resume and job description below, generate tailored resume improvements.

Return only valid JSON with this exact shape:

{{
  "tailoredExecutiveSummary": "string",
  "tailoredResumeBullets": ["string"],
  "keywordsToAdd": ["string"],
  "rolePositioningAdvice": ["string"],
  "atsOptimizationAdvice": ["string"],
  "rewriteWarnings": ["string"]
}}

Rules:
- Do not invent experience the candidate does not appear to have.
- Make bullets achievement-oriented and leadership-focused.
- Prefer measurable impact language where appropriate.
- Keep suggestions suitable for senior manager/director-level engineering roles.
- Tailor language toward the job description.

Resume:
\"\"\"
{resume_text[:8000]}
\"\"\"

Job Description:
\"\"\"
{job_description_text[:8000]}
\"\"\"
"""

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            text={
                "format": {
                    "type": "json_object"
                }
            },
        )

        parsed = json.loads(response.output_text)

        return {
            "provider": self.provider_name,
            "model": self.model,
            "analysisVersion": f"resume-tailoring-{self.model}-v1",
            "tailoredExecutiveSummary": parsed.get("tailoredExecutiveSummary", ""),
            "tailoredResumeBullets": parsed.get("tailoredResumeBullets", []),
            "keywordsToAdd": parsed.get("keywordsToAdd", []),
            "rolePositioningAdvice": parsed.get("rolePositioningAdvice", []),
            "atsOptimizationAdvice": parsed.get("atsOptimizationAdvice", []),
            "rewriteWarnings": parsed.get("rewriteWarnings", []),
        }

    def prepare_interview(self, resume_text: str, job_description_text: str) -> dict:
        prompt = f"""
You are an expert interview coach for senior software engineering managers,
cloud architects, and director-level engineering candidates.

Generate an interview preparation package based on the resume and job description.

Return only valid JSON with this exact shape:

{{
  "behavioralQuestions": [
    {{
      "question": "string",
      "answerFramework": ["string"],
      "followUpQuestions": ["string"]
    }}
  ],
  "leadershipQuestions": [
    {{
      "question": "string",
      "answerFramework": ["string"],
      "followUpQuestions": ["string"]
    }}
  ],
  "systemDesignQuestions": [
    {{
      "question": "string",
      "answerFramework": ["string"],
      "followUpQuestions": ["string"]
    }}
  ],
  "cloudArchitectureQuestions": [
    {{
      "question": "string",
      "answerFramework": ["string"],
      "followUpQuestions": ["string"]
    }}
  ],
  "securityQuestions": [
    {{
      "question": "string",
      "answerFramework": ["string"],
      "followUpQuestions": ["string"]
    }}
  ],
  "resumeSpecificQuestions": [
    {{
      "question": "string",
      "answerFramework": ["string"],
      "followUpQuestions": ["string"]
    }}
  ],
  "jobSpecificQuestions": [
    {{
      "question": "string",
      "answerFramework": ["string"],
      "followUpQuestions": ["string"]
    }}
  ],
  "interviewReadinessSummary": "string"
}}

Rules:
- Generate practical questions likely to be asked in a Director-level engineering interview.
- Make questions specific to the resume and job description.
- Include leadership, architecture, cloud, security, AI, delivery, and stakeholder themes where relevant.
- Do not invent experience. Base resume-specific questions on the resume content.
- Provide answer frameworks, not full scripted answers.
- Generate 5 questions per category.

Resume:
\"\"\"
{resume_text[:8000]}
\"\"\"

Job Description:
\"\"\"
{job_description_text[:8000]}
\"\"\"
"""

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            text={
                "format": {
                    "type": "json_object"
                }
            },
        )

        parsed = json.loads(response.output_text)

        return {
            "provider": self.provider_name,
            "model": self.model,
            "analysisVersion": f"interview-prep-{self.model}-v1",
            "behavioralQuestions": parsed.get("behavioralQuestions", []),
            "leadershipQuestions": parsed.get("leadershipQuestions", []),
            "systemDesignQuestions": parsed.get("systemDesignQuestions", []),
            "cloudArchitectureQuestions": parsed.get("cloudArchitectureQuestions", []),
            "securityQuestions": parsed.get("securityQuestions", []),
            "resumeSpecificQuestions": parsed.get("resumeSpecificQuestions", []),
            "jobSpecificQuestions": parsed.get("jobSpecificQuestions", []),
            "interviewReadinessSummary": parsed.get("interviewReadinessSummary", ""),
        }

    def _parse_json_response(self, response):
        raw_text = response.output_text.strip()

        if raw_text.startswith("```json"):
            raw_text = raw_text.removeprefix("```json").strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.removeprefix("```").strip()

        if raw_text.endswith("```"):
            raw_text = raw_text.removesuffix("```").strip()

        return json.loads(raw_text)
