"""
llm_client.py — LLM API Client
==================================
Calls the configured LLM (Gemini or OpenAI) to generate
plain-English explanations of stock predictions.

Supports:
  - Google Gemini (default, free tier available)
  - OpenAI GPT (optional fallback)

Uses the cache module to avoid redundant API calls.

Usage:
    from app.reasoning.llm_client import generate_explanation
    explanation = generate_explanation(prediction, headlines, sentiment)
"""

import logging
import time

from app.config import LLM_PROVIDER, GEMINI_API_KEY, OPENAI_API_KEY
from app.reasoning.prompt_template import build_prompt
from app.reasoning.cache import get_cached, save_to_cache

logger = logging.getLogger(__name__)

# Rate limiting — simple backoff
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def generate_explanation(
    prediction: dict,
    headlines: list[str] | None = None,
    sentiment_data: dict | None = None,
    use_cache: bool = True,
) -> str:
    """
    Generate a plain-English explanation for a prediction.

    Steps:
      1. Build the prompt from prediction data
      2. Check cache for existing explanation
      3. If not cached, call LLM API
      4. Cache the response
      5. Return the explanation text

    Args:
        prediction: dict from predict.py
        headlines: Recent news headlines
        sentiment_data: Daily sentiment scores
        use_cache: Whether to check/store in cache (default True)

    Returns:
        Plain-English explanation string.
    """
    # Step 1: Build prompt
    prompt = build_prompt(prediction, headlines, sentiment_data)

    # Step 2: Check cache
    if use_cache:
        cached = get_cached(prompt)
        if cached:
            logger.info(f"Cache hit for {prediction['ticker']} explanation")
            return cached

    # Step 3: Call LLM
    logger.info(
        f"Generating explanation for {prediction['ticker']} "
        f"via {LLM_PROVIDER}..."
    )

    explanation = _call_llm(prompt)

    # Step 4: Cache the response
    if use_cache and explanation:
        save_to_cache(prompt, explanation, model_used=LLM_PROVIDER)

    return explanation


def _call_llm(prompt: str) -> str:
    """
    Route to the configured LLM provider.
    Falls back to a template response if no API key is set.
    """
    if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
        return _call_gemini(prompt)
    elif LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        return _call_openai(prompt)
    else:
        logger.warning(
            f"No API key configured for {LLM_PROVIDER}. "
            f"Using template fallback."
        )
        return _fallback_explanation(prompt)


def _call_gemini(prompt: str) -> str:
    """Call Google Gemini API."""
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        for attempt in range(MAX_RETRIES):
            try:
                response = model.generate_content(prompt)
                return response.text.strip()

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        f"Gemini attempt {attempt + 1} failed: {e}. Retrying..."
                    )
                    time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                else:
                    raise

    except ImportError:
        logger.error("google-generativeai not installed")
        return _fallback_explanation(prompt)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return _fallback_explanation(prompt)


def _call_openai(prompt: str) -> str:
    """Call OpenAI API (fallback option)."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)

        for attempt in range(MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a financial analyst assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=300,
                    temperature=0.7,
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        f"OpenAI attempt {attempt + 1} failed: {e}. Retrying..."
                    )
                    time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                else:
                    raise

    except ImportError:
        logger.error("openai package not installed")
        return _fallback_explanation(prompt)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return _fallback_explanation(prompt)


def _fallback_explanation(prompt: str) -> str:
    """
    Generate a template-based explanation when no LLM API is available.
    Parses the prompt to extract key information and constructs a response.
    This ensures the system still works without an API key for development.
    """
    # Extract basic info from the prompt
    lines = prompt.split("\n")
    signal = "UP"
    ticker = "the stock"
    confidence = "N/A"

    for line in lines:
        if "Direction:" in line:
            signal = "UP" if "UP" in line else "DOWN"
        if "Confidence:" in line:
            confidence = line.split(":")[-1].strip().replace("%", "")
        if "analysis for" in line:
            parts = line.split("for")
            if len(parts) > 1:
                ticker = parts[1].split(",")[0].strip()

    direction = "upward" if signal == "UP" else "downward"
    sentiment = "positive" if signal == "UP" else "cautious"

    return (
        f"The model predicts an {direction} movement for {ticker} "
        f"with {confidence}% confidence. This prediction is primarily "
        f"driven by recent technical indicator trends and {sentiment} "
        f"market sentiment from news and social media analysis. "
        f"Please note this is a model prediction and should not be "
        f"treated as financial advice."
    )
