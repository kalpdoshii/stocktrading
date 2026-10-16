"""
analyzer.py — FinBERT Sentiment Analysis
============================================
Runs the ProsusAI/finbert model on financial text (news headlines,
Reddit posts) to produce sentiment scores.

FinBERT outputs three scores per text:
  - positive (0-1)
  - negative (0-1)
  - neutral (0-1)

The model is loaded once and cached for reuse within a session.

Usage:
    from app.sentiment.analyzer import analyze_sentiment
    results = analyze_sentiment(["Apple beats earnings expectations"])
    # [{"positive": 0.85, "negative": 0.05, "neutral": 0.10, "label": "positive"}]
"""

import logging
from typing import Optional

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

# Global cache for the model (loaded once, reused)
_model = None
_tokenizer = None

# FinBERT model from Hugging Face
MODEL_NAME = "ProsusAI/finbert"


def _load_model():
    """
    Load FinBERT model and tokenizer (cached globally).
    Downloads from HuggingFace on first run (~250 MB).
    """
    global _model, _tokenizer

    if _model is not None:
        return _model, _tokenizer

    logger.info(f"Loading FinBERT model: {MODEL_NAME}")
    logger.info("(First run will download ~250 MB from HuggingFace)")

    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    _model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    _model.eval()  # set to evaluation mode (no dropout)

    # Use GPU if available
    if torch.cuda.is_available():
        _model = _model.cuda()
        logger.info("FinBERT running on GPU")
    else:
        logger.info("FinBERT running on CPU")

    return _model, _tokenizer


def analyze_sentiment(
    texts: list[str],
    batch_size: int = 16,
) -> list[dict]:
    """
    Analyze sentiment for a list of texts using FinBERT.

    Args:
        texts: List of text strings to analyze.
        batch_size: How many texts to process at once.

    Returns:
        List of dicts, each with keys:
        {positive, negative, neutral, label, compound}
    """
    if not texts:
        return []

    model, tokenizer = _load_model()
    device = next(model.parameters()).device

    results = []

    # Process in batches to handle large lists
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        # Tokenize
        inputs = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        ).to(device)

        # Run inference (no gradient computation needed)
        with torch.no_grad():
            outputs = model(**inputs)
            probabilities = torch.nn.functional.softmax(
                outputs.logits, dim=-1
            )

        # FinBERT labels: 0=positive, 1=negative, 2=neutral
        for probs in probabilities:
            positive = float(probs[0])
            negative = float(probs[1])
            neutral = float(probs[2])

            # Determine dominant label
            label_idx = probs.argmax().item()
            label = ["positive", "negative", "neutral"][label_idx]

            # Compound score: positive - negative (range: -1 to +1)
            compound = positive - negative

            results.append({
                "positive": round(positive, 4),
                "negative": round(negative, 4),
                "neutral": round(neutral, 4),
                "label": label,
                "compound": round(compound, 4),
            })

    logger.info(f"Analyzed sentiment for {len(results)} texts")
    return results


def analyze_single(text: str) -> Optional[dict]:
    """Convenience function to analyze a single text."""
    if not text or not text.strip():
        return None
    results = analyze_sentiment([text])
    return results[0] if results else None
