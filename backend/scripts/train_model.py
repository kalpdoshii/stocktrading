"""
train_model.py — CLI Entry Point for Model Training
======================================================
Run from the backend directory:
    python -m scripts.train_model --mode baseline                 # baseline only
    python -m scripts.train_model --mode sentiment                # with sentiment
    python -m scripts.train_model --mode both                     # train both, compare
    python -m scripts.train_model --mode baseline --ticker AAPL   # single ticker
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ml.train_baseline import train_baseline
from app.ml.evaluate import compare_models


def main():
    parser = argparse.ArgumentParser(
        description="AI Trading Assistant — Model Training"
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "sentiment", "both"],
        default="baseline",
        help="Which model to train.",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Train for a specific ticker (default: all tickers combined).",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.mode in ("baseline", "both"):
        print("\n" + "=" * 60)
        print("TRAINING BASELINE MODEL (price + technical features)")
        print("=" * 60)
        train_baseline(ticker=args.ticker, model_version="baseline_v1")

    if args.mode in ("sentiment", "both"):
        print("\n" + "=" * 60)
        print("TRAINING SENTIMENT MODEL (price + tech + sentiment)")
        print("=" * 60)
        # Import here to avoid loading FinBERT unnecessarily
        from app.ml.train_sentiment import train_sentiment
        train_sentiment(ticker=args.ticker, model_version="sentiment_v1")

    if args.mode == "both":
        print("\n" + "=" * 60)
        print("MODEL COMPARISON")
        print("=" * 60)
        compare_models("baseline_v1", "sentiment_v1")

    print("\n✓ Training complete!")


if __name__ == "__main__":
    main()
