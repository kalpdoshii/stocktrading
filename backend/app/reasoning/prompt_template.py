"""
prompt_template.py — LLM Prompt Builder
==========================================
Builds structured prompts for the LLM to generate plain-English
explanations of stock predictions.

The prompt includes:
  - The prediction (UP/DOWN) and confidence
  - Top contributing features with values
  - Recent news headlines
  - Current sentiment score

Usage:
    from app.reasoning.prompt_template import build_prompt
    prompt = build_prompt(prediction_result, headlines, sentiment)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Main prompt template — kept clear and structured so the LLM
# produces consistent, readable explanations
EXPLANATION_TEMPLATE = """You are a financial analyst assistant explaining stock predictions to a retail investor. Be clear, concise, and avoid jargon.

Given the following analysis for {ticker}, explain the prediction in 2-3 sentences of plain English.

## Prediction
- Direction: **{signal}** (the model predicts the stock will go {signal_description} tomorrow)
- Confidence: {confidence}%

## Top Contributing Factors
{features_section}

## Recent News Headlines
{news_section}

## Sentiment Analysis
- Overall sentiment score: {sentiment_score} ({sentiment_interpretation})
- Based on analysis of {sample_count} recent news articles and social media posts

## Instructions
1. Explain WHY the model predicts {signal} for {ticker} in 2-3 sentences.
2. Reference the most important factors from above.
3. Keep it simple — this is for someone who is NOT a financial expert.
4. Do NOT give investment advice or make guarantees.
5. Start directly with the explanation, no preamble.
"""


def build_prompt(
    prediction: dict,
    headlines: list[str] | None = None,
    sentiment_data: dict | None = None,
) -> str:
    """
    Build a complete LLM prompt from prediction data.

    Args:
        prediction: dict from predict.py with keys:
            {ticker, signal, confidence, top_features, date}
        headlines: List of recent news headlines (max 5 used).
        sentiment_data: dict with {compound_score, sample_count}.

    Returns:
        Formatted prompt string ready to send to the LLM.
    """
    ticker = prediction["ticker"]
    signal = prediction["signal"]
    confidence = round(prediction["confidence"] * 100, 1)

    # Signal description
    signal_description = "up" if signal == "UP" else "down"

    # Format top features
    features_section = _format_features(prediction.get("top_features", []))

    # Format news headlines (max 5)
    news_section = _format_headlines(headlines)

    # Format sentiment
    sentiment_score, sentiment_interpretation, sample_count = _format_sentiment(
        sentiment_data
    )

    prompt = EXPLANATION_TEMPLATE.format(
        ticker=ticker,
        signal=signal,
        signal_description=signal_description,
        confidence=confidence,
        features_section=features_section,
        news_section=news_section,
        sentiment_score=sentiment_score,
        sentiment_interpretation=sentiment_interpretation,
        sample_count=sample_count,
    )

    logger.info(f"Built prompt for {ticker} ({len(prompt)} chars)")
    return prompt


def _format_features(features: list[dict]) -> str:
    """Format top features into a readable list."""
    if not features:
        return "- No feature data available"

    lines = []
    for i, feat in enumerate(features[:5], 1):
        name = feat.get("name", "unknown")
        value = feat.get("value", "N/A")
        importance = feat.get("importance", 0)

        # Make feature names more readable
        readable_name = _humanize_feature_name(name)
        lines.append(
            f"- {readable_name}: {value} "
            f"(importance rank: #{i}, weight: {importance:.3f})"
        )

    return "\n".join(lines)


def _format_headlines(headlines: list[str] | None) -> str:
    """Format recent headlines into a readable list."""
    if not headlines:
        return "- No recent headlines available"

    lines = []
    for h in headlines[:5]:
        # Truncate very long headlines
        text = h[:150] + "..." if len(h) > 150 else h
        lines.append(f'- "{text}"')

    return "\n".join(lines)


def _format_sentiment(
    sentiment_data: Optional[dict],
) -> tuple[str, str, str]:
    """Format sentiment data into readable values."""
    if not sentiment_data:
        return "N/A", "no sentiment data available", "0"

    score = sentiment_data.get("compound_score", 0)
    sample_count = sentiment_data.get("sample_count", 0)

    # Interpret the compound score
    if score > 0.3:
        interpretation = "strongly positive — bullish market sentiment"
    elif score > 0.1:
        interpretation = "mildly positive — cautiously optimistic"
    elif score > -0.1:
        interpretation = "neutral — no clear sentiment direction"
    elif score > -0.3:
        interpretation = "mildly negative — cautious market concern"
    else:
        interpretation = "strongly negative — bearish market sentiment"

    return f"{score:.3f}", interpretation, str(sample_count)


def _humanize_feature_name(name: str) -> str:
    """Convert internal feature names to readable labels."""
    mapping = {
        "sma_20": "20-day Moving Average",
        "sma_50": "50-day Moving Average",
        "ema_12": "12-day Exponential MA",
        "ema_26": "26-day Exponential MA",
        "rsi_14": "RSI (14-day)",
        "macd_line": "MACD Line",
        "macd_signal": "MACD Signal",
        "macd_histogram": "MACD Histogram",
        "bb_upper": "Bollinger Band (Upper)",
        "bb_lower": "Bollinger Band (Lower)",
        "bb_width": "Bollinger Band Width",
        "volatility_20": "20-day Volatility",
        "volume_change_pct": "Volume Change %",
        "daily_return_pct": "Daily Return %",
        "price_to_sma20": "Price/SMA20 Ratio",
        "price_to_sma50": "Price/SMA50 Ratio",
        "sentiment_compound": "Sentiment Score",
        "sentiment_positive": "Positive Sentiment",
        "sentiment_negative": "Negative Sentiment",
    }
    return mapping.get(name, name.replace("_", " ").title())
