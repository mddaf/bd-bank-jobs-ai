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
1. Determine if this is genuinely a banking/financial sector job in Bangladesh.
2. Score its relevance from 0.0 to 1.0 (1.0 = definitely a bank job in Bangladesh).
3. Categorize it (banking, finance, insurance, microfinance, investment, nbfi, government_finance, other).
4. Write a concise 2-3 sentence summary in both English and Bangla.
5. List 3-5 key requirements if identifiable.
6. Determine experience level (entry, mid, senior, any).

**Return this exact JSON structure:**
{{
    "is_relevant": true,
    "relevance_score": 0.85,
    "category": "banking",
    "summary_en": "English summary here",
    "summary_bn": "বাংলা সারাংশ এখানে",
    "key_requirements": ["Requirement 1", "Requirement 2"],
    "deadline": "extracted deadline or null",
    "experience_level": "entry",
    "estimated_salary_range": "if mentioned, else null"
}}"""

    def __init__(self, gemini_client: GeminiClient = None):
        self.client = gemini_client or GeminiClient()

    def analyze_job(self, job: dict) -> Optional[dict]:
        """
        Analyze a single job posting using Gemini AI.

        Args:
            job: Dict with keys: title, organization, description, deadline, source

        Returns:
            Analysis dict with relevance score, summaries, etc.
            Returns None if analysis fails.
        """
        prompt = self.ANALYSIS_PROMPT.format(
            title=job.get("title", "N/A"),
            organization=job.get("organization", "N/A"),
            source=job.get("source", "N/A"),
            description=(job.get("description") or "Not available")[:1000],
            deadline=job.get("deadline") or "Not specified",
        )

        result = self.client.generate_json(prompt)

        if result:
            # Validate and normalize the response
            result = self._normalize_analysis(result)
            logger.info(
                f"Analyzed: {job.get('title', '?')} @ {job.get('organization', '?')} "
                f"→ score={result.get('relevance_score', 0):.2f}, "
                f"category={result.get('category', '?')}"
            )
        else:
            logger.warning(f"Failed to analyze: {job.get('title', '?')}")
            # Return a default analysis so the job isn't stuck forever
            result = self._default_analysis(job)

        return result

    BATCH_PROMPT = """You are an expert job analyst specializing in Bangladesh's banking and financial sector.

Analyze the following list of job postings and return a JSON array with analysis for each item.

Jobs to analyze:
{jobs_json}

For each job, evaluate:
1. is_relevant: true if this is a genuine employment opportunity in banking/finance/NBFI in Bangladesh; false if it's board members, executive council, annual report, notice, tender, or non-job.
2. relevance_score: 0.0 to 1.0 (0.0 for non-jobs, 1.0 for core bank jobs)
3. category: banking, finance, insurance, microfinance, investment, nbfi, government_finance, or other
4. summary_en: concise 1-2 sentence English summary
5. summary_bn: concise 1-2 sentence Bangla summary
6. key_requirements: array of 2-4 key requirements strings
7. deadline: extracted deadline or null
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

    def analyze_batch(self, jobs: list, batch_size: int = 3, max_jobs: int = 50) -> list:
        """
        Analyze multiple jobs in batches using Gemini AI for high throughput.
        Falls back to individual analysis if a batch fails.

        Args:
            jobs: List of job dicts
            batch_size: Number of jobs to process per Gemini prompt
            max_jobs: Maximum number to analyze in total

        Returns:
            List of (job, analysis) tuples
        """
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
                # Map results by id
                resp_map = {item.get("id"): item for item in batch_resp if isinstance(item, dict) and "id" in item}
                for idx, job in enumerate(chunk, start=i):
                    job_id = job.get("id", idx)
                    analysis = resp_map.get(job_id)
                    if not analysis and idx < len(batch_resp):
                        analysis = batch_resp[idx - i]

                    if analysis:
                        normalized = self._normalize_analysis(analysis)
                        logger.info(
                            f"  ✅ [{normalized.get('relevance_score', 0):.0%}] "
                            f"{job.get('title', '?')[:35]} @ {job.get('organization', '?')[:25]}"
                        )
                        results.append((job, normalized))
                    else:
                        results.append((job, self.analyze_job(job)))
            else:
                logger.warning(f"Batch analysis returned non-list or failed. Falling back to individual analysis for {len(chunk)} jobs...")
                for job in chunk:
                    results.append((job, self.analyze_job(job)))

        return results

    def _normalize_analysis(self, result: dict) -> dict:
        """Ensure all expected fields exist with valid values."""
        return {
            "is_relevant": result.get("is_relevant", True),
            "relevance_score": max(0.0, min(1.0, float(result.get("relevance_score", 0.5)))),
            "category": result.get("category", "unknown"),
            "summary_en": result.get("summary_en", "No summary available."),
            "summary_bn": result.get("summary_bn", "সারাংশ পাওয়া যায়নি।"),
            "key_requirements": result.get("key_requirements", []),
            "deadline": result.get("deadline"),
            "experience_level": result.get("experience_level", "any"),
            "estimated_salary_range": result.get("estimated_salary_range"),
        }

    def _default_analysis(self, job: dict) -> dict:
        """Create a default analysis when Gemini fails."""
        org = job.get("organization", "").lower()
        title = job.get("title", "").lower()

        # Simple keyword-based relevance scoring
        score = 0.5
        banking_keywords = ["bank", "ব্যাংক", "finance", "অর্থ", "loan", "credit"]
        for kw in banking_keywords:
            if kw in org or kw in title:
                score = 0.7
                break

        return {
            "is_relevant": score > 0.4,
            "relevance_score": score,
            "category": "banking" if "bank" in org.lower() else "finance",
            "summary_en": f"Job posting: {job.get('title', 'N/A')} at {job.get('organization', 'N/A')}",
            "summary_bn": f"চাকরির বিজ্ঞপ্তি: {job.get('title', 'N/A')} - {job.get('organization', 'N/A')}",
            "key_requirements": [],
            "deadline": job.get("deadline"),
            "experience_level": "any",
            "estimated_salary_range": None,
        }
