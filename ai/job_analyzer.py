"""
Job Analyzer — Gemini-Powered Intelligence
=============================================
Uses Gemini AI to analyze job postings:
  - Determine relevance to banking/finance
  - Generate bilingual summaries (English + Bangla)
  - Extract key requirements
  - Score job relevance (0.0 — 1.0)
"""

import logging
import re
from typing import Optional
from ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class JobAnalyzer:
    """
    Analyzes job postings using Gemini AI to determine
    relevance and generate useful summaries.
    """

    ANALYSIS_PROMPT = """You are an expert job analyst specializing in Bangladesh's banking and financial sector.

Analyze the following job posting and return a JSON response.

**Job Information:**
- Title: {title}
- Organization: {organization}
- Source: {source}
- Description: {description}
- Deadline: {deadline}

**Instructions:**
1. Determine if this is genuinely a banking/financial sector job opening in Bangladesh.
2. CRITICAL: Reject if this is a corporate governance page (e.g. Board of Directors, Audit Committee, CEO profile), annual report, tender, policy, or generic notice. Set is_relevant=false, relevance_score=0.0.
3. Score genuine banking/finance jobs from 0.7 to 1.0.
4. Categorize it (banking, finance, insurance, microfinance, investment, nbfi, government_finance, other).
5. Write a concise 2-sentence summary in both English and Bangla focusing on role and responsibilities.
6. List 2-4 key requirements if identifiable.
7. Determine experience level (entry, mid, senior, any).

**Return this exact JSON structure:**
{{
    "is_relevant": true,
    "relevance_score": 0.90,
    "category": "banking",
    "summary_en": "English summary here",
    "summary_bn": "বাংলা সারাংশ এখানে",
    "key_requirements": ["Requirement 1", "Requirement 2"],
    "deadline": "extracted deadline or null",
    "experience_level": "entry",
    "estimated_salary_range": "if mentioned, else null"
}}"""

    BATCH_PROMPT = """You are an expert job analyst specializing in Bangladesh's banking and financial sector.

Analyze the following list of job postings and return a JSON array with analysis for each item.

Jobs to analyze:
{jobs_json}

For each job, evaluate:
1. is_relevant: TRUE if this is a genuine employment vacancy/job circular in banking, financial institutions, or NBFIs in Bangladesh; FALSE if it is a corporate governance page, board of directors, management profile, annual report, notice, or tender.
2. relevance_score: 0.0 for non-jobs; 0.70 to 1.0 for genuine bank/financial jobs.
3. category: banking, finance, insurance, microfinance, investment, nbfi, government_finance, or other
4. summary_en: concise 1-2 sentence English summary of the position
5. summary_bn: concise 1-2 sentence Bangla summary of the position
6. key_requirements: array of 2-4 requirements strings
7. deadline: application deadline or null
8. experience_level: entry, mid, senior, or any
9. estimated_salary_range: if mentioned, else null

Return ONLY a valid JSON array matching this format:
[
  {{
    "id": <job_id>,
    "is_relevant": true,
    "relevance_score": 0.85,
    "category": "banking",
    "summary_en": "...",
    "summary_bn": "...",
    "key_requirements": ["..."],
    "deadline": "...",
    "experience_level": "entry",
    "estimated_salary_range": null
  }}
]"""

    def __init__(self, gemini_client: GeminiClient = None):
        self.client = gemini_client or GeminiClient()

    def analyze_job(self, job: dict) -> Optional[dict]:
        """Analyze a single job posting using Gemini AI."""
        # Pre-check: Reject obvious governance/non-job records before calling API
        if not self._is_candidate_job(job):
            return self._rejected_analysis(job)

        prompt = self.ANALYSIS_PROMPT.format(
            title=job.get("title", "N/A"),
            organization=job.get("organization", "N/A"),
            source=job.get("source", "N/A"),
            description=(job.get("description") or "Not available")[:1000],
            deadline=job.get("deadline") or "Not specified",
        )

        result = self.client.generate_json(prompt)

        if result:
            result = self._normalize_analysis(result)
            logger.info(
                f"Analyzed: {job.get('title', '?')} @ {job.get('organization', '?')} "
                f"→ score={result.get('relevance_score', 0):.2f}, "
                f"category={result.get('category', '?')}"
            )
        else:
            logger.warning(f"Gemini API returned None for {job.get('title', '?')}, using smart local fallback")
            result = self._default_analysis(job)

        return result

    def analyze_batch(self, jobs: list, batch_size: int = 3, max_jobs: int = 50) -> list:
        """Analyze multiple jobs in batches using Gemini AI."""
        import json
        target_jobs = jobs[:max_jobs]
        results = []

        for i in range(0, len(target_jobs), batch_size):
            chunk = target_jobs[i : i + batch_size]
            logger.info(f"Analyzing batch {i//batch_size + 1}/{(len(target_jobs) + batch_size - 1)//batch_size} ({len(chunk)} jobs)...")

            simplified_chunk = [
                {
                    "id": job.get("id", idx),
                    "title": job.get("title", "N/A"),
                    "organization": job.get("organization", "N/A"),
                    "description": (job.get("description") or "Not available")[:300],
                    "deadline": job.get("deadline") or "Not specified",
                    "source": job.get("source", "N/A"),
                }
                for idx, job in enumerate(chunk, start=i)
            ]

            prompt = self.BATCH_PROMPT.format(jobs_json=json.dumps(simplified_chunk, ensure_ascii=False, indent=2))
            batch_resp = self.client.generate_json(prompt)

            if isinstance(batch_resp, list) and len(batch_resp) > 0:
                resp_map = {item.get("id"): item for item in batch_resp if isinstance(item, dict) and "id" in item}
                for idx, job in enumerate(chunk, start=i):
                    job_id = job.get("id", idx)
                    analysis = resp_map.get(job_id)
                    if not analysis and idx < len(batch_resp):
                        analysis = batch_resp[idx - i]

                    if analysis:
                        normalized = self._normalize_analysis(analysis)
                        results.append((job, normalized))
                    else:
                        results.append((job, self.analyze_job(job)))
            else:
                logger.warning(f"Batch analysis failed or returned non-list. Processing individual jobs in batch...")
                for job in chunk:
                    results.append((job, self.analyze_job(job)))

        return results

    def _is_candidate_job(self, job: dict) -> bool:
        """Heuristic check: returns False if title contains governance or non-job keywords."""
        title = (job.get("title") or "").lower()
        non_job_patterns = [
            "board of director", "managing director & ceo", "executive committee",
            "audit committee", "shariah council", "annual report", "code of conduct",
            "citizen charter", "independent director", "chairman message",
            "tender", "schedule of charges", "rates of interest", "branch locator",
        ]
        if any(p in title for p in non_job_patterns):
            return False
        return True

    def _rejected_analysis(self, job: dict) -> dict:
        """Explicit rejection for non-job items."""
        return {
            "is_relevant": False,
            "relevance_score": 0.0,
            "category": "non_job",
            "summary_en": "Not an employment opportunity.",
            "summary_bn": "কোনো চাকরির বিজ্ঞপ্তি নয়।",
            "key_requirements": [],
            "deadline": None,
            "experience_level": "none",
            "estimated_salary_range": None,
        }

    def _normalize_analysis(self, result: dict) -> dict:
        """Ensure all expected fields exist with valid values."""
        return {
            "is_relevant": bool(result.get("is_relevant", True)),
            "relevance_score": max(0.0, min(1.0, float(result.get("relevance_score", 0.5)))),
            "category": result.get("category", "banking"),
            "summary_en": result.get("summary_en", "Bank job opening in Bangladesh."),
            "summary_bn": result.get("summary_bn", "বাংলাদেশের ব্যাংকিং খাতের চাকরির বিজ্ঞপ্তি।"),
            "key_requirements": result.get("key_requirements", []),
            "deadline": result.get("deadline"),
            "experience_level": result.get("experience_level", "any"),
            "estimated_salary_range": result.get("estimated_salary_range"),
        }

    def _default_analysis(self, job: dict) -> dict:
        """Intelligent local fallback analysis when Gemini API is unavailable."""
        title = (job.get("title") or "").lower()
        org = (job.get("organization") or "").lower()

        if not self._is_candidate_job(job):
            return self._rejected_analysis(job)

        # Genuine job designation indicators
        job_roles = [
            "officer", "manager", "executive", "analyst", "teller",
            "assistant", "trainee", "associate", "specialist", "engineer",
            "developer", "clerk", "operator", "নিয়োগ", "বিজ্ঞপ্তি", "কর্মকর্তা", "পদ"
        ]

        has_job_role = any(r in title for r in job_roles)
        if not has_job_role:
            return self._rejected_analysis(job)

        score = 0.85
        category = "government_finance" if any(k in org for k in ["bangladesh bank", "sonali", "janata", "agrani", "rupali", "bscs"]) else "banking"

        title_display = job.get("title", "Position")
        org_display = job.get("organization", "Banking Institution")

        return {
            "is_relevant": True,
            "relevance_score": score,
            "category": category,
            "summary_en": f"Official vacancy for {title_display} at {org_display}.",
            "summary_bn": f"{org_display}-এ {title_display} পদের জন্য নিয়োগ বিজ্ঞপ্তি।",
            "key_requirements": ["Relevant educational qualification in accordance with official circular."],
            "deadline": job.get("deadline"),
            "experience_level": "entry" if any(w in title for w in ["trainee", "assistant", "junior", "entry"]) else "mid",
            "estimated_salary_range": None,
        }
