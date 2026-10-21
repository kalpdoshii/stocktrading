"""
train_model.py — CLI Entry Point for Model Training & Validation
================================================================
Run from backend directory:
    python -m scripts.train_model --mode baseline
    python -m scripts.train_model --mode sentiment
    python -m scripts.train_model --mode both --ticker RELIANCE.NS
    python -m scripts.train_model --mode both --walk-forward --ticker RELIANCE.NS
    python -m scripts.train_model --mode compare-aligned --ticker RELIANCE.NS
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ml.evaluate import compare_models
from app.ml.train_baseline import train_baseline
from app.ml.train_sentiment import train_sentiment, train_and_compare_models


def main():
    parser = argparse.ArgumentParser(description="AI Trading Assistant — Model Training & Walk-Forward Validation")
    parser.add_argument(
        "--mode",
        choices=["baseline", "sentiment", "both", "compare-aligned"],
        default="both",
        help="Model mode to train or compare.",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Train for a specific ticker (default: all tickers combined).",
    )
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="Execute chronological 5-fold walk-forward cross-validation.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.55,
        help="Confidence threshold for abstention (default: 0.55).",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.mode == "compare-aligned":
        ticker = args.ticker or "RELIANCE.NS"
        print("\n" + "=" * 65)
        print(f"RUNNING SYNCHRONIZED PAIRED MODEL COMPARISON ({ticker})")
        print("Identical dataset, identical test period, calibrated probabilities")
        print("=" * 65)
        train_and_compare_models(ticker)
        return

    if args.mode in ("baseline", "both"):
        print("\n" + "=" * 65)
        print("TRAINING BASELINE MODEL (price + technical features)")
        print("=" * 65)
        train_baseline(
            ticker=args.ticker,
            model_version="baseline_v1",
            run_walk_forward=args.walk_forward,
            confidence_threshold=args.threshold,
        )

    if args.mode in ("sentiment", "both"):
        print("\n" + "=" * 65)
        print("TRAINING SENTIMENT-AUGMENTED MODEL (price + tech + FinBERT)")
        print("=" * 65)
        train_sentiment(
            ticker=args.ticker,
            model_version="sentiment_v1",
            run_walk_forward=args.walk_forward,
            confidence_threshold=args.threshold,
        )

    if args.mode == "both":
        print("\n" + "=" * 65)
        print("MODEL COMPARISON (Baseline vs. Sentiment)")
        print("=" * 65)
        compare_models("baseline_v1", "sentiment_v1")

    print("\n[OK] Model training & evaluation complete!")


if __name__ == "__main__":
    main()
