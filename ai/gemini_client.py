"""
Gemini AI Client
==================
Wrapper around the Google Generative AI SDK for Gemini.
Handles API key configuration, rate limiting, and error handling.
"""

import time
import json
import logging
from typing import Optional
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_RATE_LIMIT_PER_MINUTE, GEMINI_FALLBACK_MODELS

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client for Google Gemini AI API.
    Manages rate limiting, automatic fallback across models, and error handling.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError(
                "Gemini API key not configured! "
                "Set GEMINI_API_KEY in your .env file. "
                "Get one free at: https://aistudio.google.com/apikey"
            )

        genai.configure(api_key=self.api_key)
        self._models = list(GEMINI_FALLBACK_MODELS) if GEMINI_FALLBACK_MODELS else [GEMINI_MODEL]
        self._model_index = 0
        self.current_model = self._models[0]
        self.model = genai.GenerativeModel(self.current_model)
        self._request_times = []
        self._rate_limit = GEMINI_RATE_LIMIT_PER_MINUTE
        self.quota_exhausted = False
        logger.info(f"Gemini client initialized with model: {self.current_model}")

    def _try_fallback_model(self) -> bool:
        """Switch to next fallback model if current model's quota is exhausted."""
        if self._model_index + 1 < len(self._models):
            self._model_index += 1
            self.current_model = self._models[self._model_index]
            self.model = genai.GenerativeModel(self.current_model)
            logger.info(f"Switched to fallback model: {self.current_model}")
            return True
        return False

    def _enforce_rate_limit(self):
        """Ensure we don't exceed the per-minute rate limit."""
        now = time.time()
        self._request_times = [t for t in self._request_times if now - t < 60]

        if len(self._request_times) >= self._rate_limit:
            wait_time = 60 - (now - self._request_times[0]) + 1
            logger.info(f"Rate limit reached. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)

        self._request_times.append(time.time())

    def generate(self, prompt: str, max_retries: int = 2, response_mime_type: Optional[str] = None) -> Optional[str]:
        """
        Generate text using Gemini.
        Returns generated text string, or None if quota exhausted / failure.
        """
        if self.quota_exhausted:
            return None

        for attempt in range(1, max_retries + 1):
            try:
                self._enforce_rate_limit()

                logger.debug(f"Sending prompt to Gemini ({len(prompt)} chars)")
                config_kwargs = {
                    "temperature": 0.3,
                    "max_output_tokens": 4096,
                }
                if response_mime_type:
                    config_kwargs["response_mime_type"] = response_mime_type

                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(**config_kwargs),
                )

                if response and response.text:
                    logger.debug(f"Gemini response: {len(response.text)} chars")
                    return response.text
                else:
                    logger.warning(f"Empty response from Gemini (attempt {attempt})")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Gemini API error (attempt {attempt}/{max_retries}): {error_msg}")

                if "quota" in error_msg.lower() or "resourceexhausted" in error_msg.lower():
                    logger.warning(f"API daily quota reached for model {self.current_model}.")
                    if self._try_fallback_model():
                        continue
                    self.quota_exhausted = True
                    logger.warning("All Gemini model quotas reached. Switching to instant local analysis.")
                    return None
                elif "404" in error_msg or "not found" in error_msg.lower():
                    if self._try_fallback_model():
                        continue
                    self.quota_exhausted = True
                    return None
                elif "429" in error_msg or "rate" in error_msg.lower():
                    if self._try_fallback_model():
                        continue
                    self.quota_exhausted = True
                    return None
                elif attempt < max_retries:
                    time.sleep(1)

        return None

    def generate_json(self, prompt: str) -> Optional[dict]:
        """
        Generate a JSON response from Gemini.
        Automatically parses the response and handles common formatting issues.
        """
        full_prompt = prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON."

        response = self.generate(full_prompt, response_mime_type="application/json")
        if not response:
            return None

        # Try to extract JSON from response
        return self._parse_json_response(response)

    def _parse_json_response(self, text: str) -> Optional[dict]:
        """Parse a JSON response, handling common formatting issues."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text, strict=False)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            logger.debug(f"Raw response: {text[:500]}")

            # Try to find JSON object or array in the text
            try:
                start = text.index("{")
                end = text.rindex("}") + 1
                return json.loads(text[start:end], strict=False)
            except (ValueError, json.JSONDecodeError):
                pass

            try:
                start = text.index("[")
                end = text.rindex("]") + 1
                return json.loads(text[start:end], strict=False)
            except (ValueError, json.JSONDecodeError):
                logger.error("Could not extract valid JSON from response")
                return None
