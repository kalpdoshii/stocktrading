"""
cache.py — LLM Response Cache
=================================
Caches LLM API responses in MySQL to avoid redundant API calls.
Uses SHA-256 hash of the prompt as the cache key.

Cache hits save API quota and reduce latency significantly.

Usage:
    from app.reasoning.cache import get_cached, save_to_cache
    cached = get_cached(prompt_text)
    if not cached:
        response = call_llm(prompt_text)
        save_to_cache(prompt_text, response)
"""

import hashlib
import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import LLMCache

logger = logging.getLogger(__name__)


def _hash_prompt(prompt: str) -> str:
    """
    Generate a SHA-256 hash of the prompt text.
    This is used as the cache key for quick lookups.
    """
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def get_cached(prompt: str) -> str | None:
    """
    Check if we already have a cached LLM response for this prompt.

    Args:
        prompt: The full prompt text.

    Returns:
        The cached response text, or None if not found.
    """
    prompt_hash = _hash_prompt(prompt)

    db: Session = SessionLocal()
    try:
        cached = (
            db.query(LLMCache)
            .filter(LLMCache.prompt_hash == prompt_hash)
            .first()
        )

        if cached:
            logger.debug(f"Cache hit: {prompt_hash[:12]}...")
            return cached.response_text

        return None

    finally:
        db.close()


def save_to_cache(
    prompt: str,
    response: str,
    model_used: str = "unknown",
) -> None:
    """
    Save an LLM response to the cache.

    Args:
        prompt: The full prompt text.
        response: The LLM's response text.
        model_used: Which LLM model was used (e.g. "gemini", "openai").
    """
    prompt_hash = _hash_prompt(prompt)

    db: Session = SessionLocal()
    try:
        # Check if already cached (race condition protection)
        existing = (
            db.query(LLMCache)
            .filter(LLMCache.prompt_hash == prompt_hash)
            .first()
        )

        if existing:
            logger.debug(f"Cache entry already exists: {prompt_hash[:12]}...")
            return

        entry = LLMCache(
            prompt_hash=prompt_hash,
            prompt_text=prompt[:5000],  # truncate very long prompts
            response_text=response,
            model_used=model_used,
        )
        db.add(entry)
        db.commit()
        logger.info(f"Cached LLM response: {prompt_hash[:12]}...")

    except Exception as e:
        logger.error(f"Error saving to cache: {e}")
        db.rollback()
    finally:
        db.close()


def clear_cache() -> int:
    """
    Clear all cached LLM responses.
    Returns the number of entries deleted.
    """
    db: Session = SessionLocal()
    try:
        count = db.query(LLMCache).count()
        db.query(LLMCache).delete()
        db.commit()
        logger.info(f"Cleared {count} cache entries")
        return count
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        db.rollback()
        return 0
    finally:
        db.close()
