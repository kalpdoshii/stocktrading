"""
reasoning.py — LLM Explanation API Endpoints
================================================
GET /api/explain/{ticker}  → LLM-generated explanation for latest prediction
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import TICKERS
from app.models import Prediction, SentimentScore, NewsHeadline

router = APIRouter(tags=["Reasoning"])


@router.get("/explain/{ticker}")
def get_explanation(ticker: str, db: Session = Depends(get_db)):
    """
    Get a plain-English LLM explanation for the latest prediction.

    Gathers context (prediction, headlines, sentiment), builds a
    prompt, and returns the LLM's explanation.
    """
    ticker = ticker.upper()

    if ticker not in TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not configured")

    # Get latest prediction
    prediction = (
        db.query(Prediction)
        .filter(Prediction.ticker == ticker)
        .order_by(Prediction.date.desc())
        .first()
    )

    if not prediction:
        # Try generating a prediction first
        try:
            from app.ml.predict import predict_ticker
            pred_result = predict_ticker(ticker)
        except Exception:
            raise HTTPException(
                status_code=404,
                detail=f"No prediction available for {ticker}. Run the model first."
            )
    else:
        import json
        features = prediction.features_json
        if isinstance(features, str):
            features = json.loads(features)

        pred_result = {
            "ticker": ticker,
            "signal": prediction.signal_dir,
            "confidence": prediction.confidence,
            "top_features": features or [],
            "date": str(prediction.date),
        }

    # Get recent headlines
    headlines_rows = (
        db.query(NewsHeadline)
        .filter(NewsHeadline.ticker == ticker)
        .order_by(NewsHeadline.published_at.desc())
        .limit(5)
        .all()
    )
    headlines = [h.headline for h in headlines_rows if h.headline]

    # Get latest sentiment
    sentiment_row = (
        db.query(SentimentScore)
        .filter(
            SentimentScore.ticker == ticker,
            SentimentScore.source_type == "combined",
        )
        .order_by(SentimentScore.date.desc())
        .first()
    )

    sentiment_data = None
    if sentiment_row:
        sentiment_data = {
            "compound_score": sentiment_row.compound_score,
            "sample_count": sentiment_row.sample_count,
        }

    # Generate explanation via LLM
    try:
        from app.reasoning.llm_client import generate_explanation
        explanation = generate_explanation(pred_result, headlines, sentiment_data)
    except Exception as e:
        explanation = (
            f"Unable to generate explanation: {str(e)}. "
            f"The model predicts {pred_result['signal']} for {ticker} "
            f"with {pred_result['confidence']:.0%} confidence."
        )

    return {
        "ticker": ticker,
        "prediction": pred_result,
        "explanation": explanation,
        "headlines_used": headlines,
        "sentiment": sentiment_data,
    }
