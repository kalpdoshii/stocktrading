"""
run_backtest.py — CLI Entry Point for Backtesting
====================================================
Run from the backend directory:
    python -m scripts.run_backtest --ticker AAPL
    python -m scripts.run_backtest --ticker AAPL --model baseline_v1
    python -m scripts.run_backtest --all                    # all tickers
"""

import argparse
import json
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import TICKERS
from app.backtesting.engine import run_backtest
from app.database import SessionLocal
from app.models import BacktestResult


def save_backtest_to_db(result: dict) -> None:
    """Persist backtest results to the backtest_results table."""
    db = SessionLocal()
    try:
        record = BacktestResult(
            ticker=result["ticker"],
            model_version=result["model_version"],
            start_date=result["start_date"],
            end_date=result["end_date"],
            total_trades=result["metrics"]["total_trades"],
            winning_trades=result["metrics"]["winning_trades"],
            losing_trades=result["metrics"]["losing_trades"],
            total_return_pct=result["metrics"]["total_return_pct"],
            win_rate=result["metrics"]["win_rate"],
            sharpe_ratio=result["metrics"]["sharpe_ratio"],
            transaction_costs=result["metrics"]["transaction_costs"],
            benchmark_return_pct=result["metrics"]["benchmark_return_pct"],
            excess_return_pct=result["metrics"]["excess_return_pct"],
            equity_curve_json=json.dumps(result["equity_curve"]),
        )
        db.add(record)
        db.commit()
        logging.info(f"Backtest results saved to DB for {result['ticker']}")
    except Exception as e:
        logging.error(f"Error saving backtest: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="AI Trading Assistant — Backtesting"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Ticker to backtest (e.g. AAPL).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Backtest all configured tickers.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="sentiment_v1",
        help="Model version to use (default: sentiment_v1).",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        help="Starting capital (default: $10,000).",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    tickers_to_test = []
    if args.all:
        tickers_to_test = TICKERS
    elif args.ticker:
        tickers_to_test = [args.ticker]
    else:
        print("Please specify --ticker AAPL or --all")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("BACKTESTING")
    print("=" * 60)

    for ticker in tickers_to_test:
        try:
            print(f"\n--- {ticker} ---")
            result = run_backtest(
                ticker,
                model_version=args.model,
                initial_capital=args.capital,
            )

            # Save to DB
            save_backtest_to_db(result)

            # Print summary
            m = result["metrics"]
            print(f"  Total Return:  {m['total_return_pct']:+.2f}%")
            print(f"  Final Value:   ${m['final_value']:,.2f}")
            print(f"  Win Rate:      {m['win_rate']:.1f}%")
            print(f"  Sharpe Ratio:  {m['sharpe_ratio']:.3f}")
            print(f"  Max Drawdown:  {m['max_drawdown_pct']:.1f}%")
            print(f"  Total Trades:  {m['total_trades']}")

        except Exception as e:
            print(f"  Error: {e}")

    print("\n✓ Backtesting complete!")


if __name__ == "__main__":
    main()
