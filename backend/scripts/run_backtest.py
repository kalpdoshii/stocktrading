"""
run_backtest.py — CLI Entry Point for Backtesting v2
=======================================================
Run from the backend directory:
    python -m scripts.run_backtest --ticker RELIANCE.NS
    python -m scripts.run_backtest --ticker RELIANCE.NS --strategy sma_crossover
    python -m scripts.run_backtest --ticker RELIANCE.NS --strategy buy_and_hold
    python -m scripts.run_backtest --all --strategy ml_signal
    python -m scripts.run_backtest --compare --ticker RELIANCE.NS
"""

import argparse
import json
import logging
import sys
import os

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import TICKERS
from app.backtesting.engine import run_backtest
from app.backtesting.strategies import STRATEGY_REGISTRY
from app.database import SessionLocal
from app.models import BacktestResult


def save_backtest_to_db(result: dict) -> None:
    """Persist backtest results to the backtest_results table."""
    db = SessionLocal()
    try:
        record = BacktestResult(
            ticker=result["ticker"],
            model_version=result.get("model_version") or result["strategy"]["name"],
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


def _print_metrics(m: dict) -> None:
    """Pretty-print backtest metrics."""
    print(f"  Total Return:       {m['total_return_pct']:+.2f}%")
    print(f"  CAGR:               {m.get('cagr_pct', 'N/A')}%")
    print(f"  Annual Volatility:  {m.get('annual_volatility_pct', 'N/A')}%")
    print(f"  Final Value:        ${m['final_value']:,.2f}")
    print(f"  Win Rate:           {m['win_rate']:.1f}%")
    print(f"  Sharpe Ratio:       {m['sharpe_ratio']:.3f}")
    print(f"  Sortino Ratio:      {m.get('sortino_ratio', 'N/A')}")
    print(f"  Max Drawdown:       {m['max_drawdown_pct']:.1f}%")
    print(f"  Max DD Duration:    {m.get('max_drawdown_duration_days', 'N/A')} days")
    print(f"  Profit Factor:      {m.get('profit_factor', 'N/A')}")
    print(f"  Trade Expectancy:   {m.get('trade_expectancy', 'N/A')}")
    print(f"  Turnover:           {m.get('turnover_pct', 'N/A')}%")
    print(f"  Total Trades:       {m['total_trades']}")
    print(f"  Transaction Costs:  ${m['transaction_costs']:.2f}")


def main():
    parser = argparse.ArgumentParser(
        description="AI Trading Assistant - Backtesting v2"
    )
    parser.add_argument(
        "--ticker", type=str, default=None,
        help="Ticker to backtest (e.g. RELIANCE.NS).",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Backtest all configured tickers.",
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Compare all strategies for one ticker.",
    )
    parser.add_argument(
        "--strategy", type=str, default="ml_signal",
        help="Strategy: buy_and_hold, sma_crossover, rsi_mean_reversion, ml_signal, or all.",
    )
    parser.add_argument(
        "--model", type=str, default="sentiment_v1",
        help="Model version (for ml_signal strategy).",
    )
    parser.add_argument(
        "--capital", type=float, default=10000.0,
        help="Starting capital (default: $10,000).",
    )
    parser.add_argument(
        "--execution", type=str, default="next_open",
        choices=["next_open", "same_close"],
        help="Execution timing (default: next_open).",
    )
    parser.add_argument(
        "--sizing", type=str, default="all_in",
        choices=["all_in", "fixed_fraction", "volatility_adjusted"],
        help="Position sizing mode.",
    )
    parser.add_argument(
        "--fraction", type=float, default=0.20,
        help="Position fraction (for fixed_fraction sizing).",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ---------- Multi-strategy comparison mode ----------
    if args.compare or args.strategy == "all":
        if not args.ticker:
            print("--compare requires --ticker")
            sys.exit(1)

        strategies = ["buy_and_hold", "sma_crossover", "rsi_mean_reversion"]
        # Only add ml_signal if a model exists
        try:
            from app.ml.predict import load_model_artifact
            load_model_artifact(args.model)
            strategies.append("ml_signal")
        except Exception:
            print("  [WARN] Skipping ml_signal (no trained model found)")

        print(f"\n{'=' * 70}")
        print(f"STRATEGY COMPARISON - {args.ticker}")
        print(f"{'=' * 70}")

        for strat in strategies:
            try:
                print(f"\n{'-' * 50}")
                print(f"  Strategy: {strat}")
                print(f"{'-' * 50}")
                result = run_backtest(
                    args.ticker,
                    strategy_name=strat,
                    model_version=args.model,
                    initial_capital=args.capital,
                    execution_timing=args.execution,
                    position_sizing=args.sizing,
                    position_fraction=args.fraction,
                )
                _print_metrics(result["metrics"])
            except Exception as e:
                print(f"  Error: {e}")

        print(f"\n[OK] Comparison complete!")
        return

    # ---------- Single or multi-ticker mode ----------
    tickers_to_test = []
    if args.all:
        tickers_to_test = TICKERS
    elif args.ticker:
        tickers_to_test = [args.ticker]
    else:
        print("Please specify --ticker SYMBOL or --all")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(f"BACKTESTING ({args.strategy}, {args.execution}, {args.sizing})")
    print("=" * 60)

    for ticker in tickers_to_test:
        try:
            print(f"\n--- {ticker} ---")
            result = run_backtest(
                ticker,
                strategy_name=args.strategy,
                model_version=args.model,
                initial_capital=args.capital,
                execution_timing=args.execution,
                position_sizing=args.sizing,
                position_fraction=args.fraction,
            )

            # Save to DB
            save_backtest_to_db(result)
            _print_metrics(result["metrics"])

            # Print disclaimer
            if result.get("disclaimer"):
                print(f"\n  [DISCLAIMER] {result['disclaimer']}")

        except Exception as e:
            print(f"  Error: {e}")

    print("\n[OK] Backtesting complete!")


if __name__ == "__main__":
    main()
