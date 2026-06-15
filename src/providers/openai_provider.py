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

    def analyze(self, resume_text: str) -> dict:
        prompt = f"""
You are an expert resume coach for senior software engineering leaders, cloud architects, and engineering managers.

Analyze the resume below and return only valid JSON with this exact shape:

{{
  "score": 0,
  "leadershipScore": 0,
  "technicalScore": 0,
  "architectureScore": 0,
  "atsScore": 0,
  "wordCount": 0,
  "strengths": ["string"],
  "recommendations": ["string"],
  "leadershipGaps": ["string"],
  "technicalGaps": ["string"],
  "executiveSummary": "string"
}}

Scoring rules:
- score: overall resume quality from 0 to 100
- leadershipScore: leadership positioning from 0 to 100
- technicalScore: technical credibility from 0 to 100
- architectureScore: cloud/software architecture positioning from 0 to 100
- atsScore: keyword and scanability strength from 0 to 100

Resume:
\"\"\"
{resume_text[:2000000]}
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

        raw_text = response.output_text
        parsed = json.loads(raw_text)

        return {
            "provider": self.provider_name,
            "model": self.model,
            "analysisVersion": self.analysis_version,
            "score": int(parsed.get("score", 0)),
            "leadershipScore": int(parsed.get("leadershipScore", 0)),
            "technicalScore": int(parsed.get("technicalScore", 0)),
            "architectureScore": int(parsed.get("architectureScore", 0)),
            "atsScore": int(parsed.get("atsScore", 0)),
            "wordCount": int(parsed.get("wordCount", len(resume_text.split()))),
            "strengths": parsed.get("strengths", []),
            "recommendations": parsed.get("recommendations", []),
            "leadershipGaps": parsed.get("leadershipGaps", []),
            "technicalGaps": parsed.get("technicalGaps", []),
            "executiveSummary": parsed.get("executiveSummary", ""),
        }
