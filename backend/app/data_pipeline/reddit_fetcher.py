"""
reddit_fetcher.py — Reddit Posts/Comments via PRAW
====================================================
Searches finance subreddits for ticker mentions using the Reddit API.
Stores posts and top comments in the `reddit_posts` MySQL table.

Subreddits searched: wallstreetbets, stocks, investing (configurable).

Usage:
    from app.data_pipeline.reddit_fetcher import fetch_reddit
    fetch_reddit(["AAPL", "TSLA"])
    fetch_reddit()  # all configured tickers
"""

import logging
from datetime import datetime

import praw
from sqlalchemy.orm import Session

from app.config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    TICKERS,
    SUBREDDITS,
)
from app.database import SessionLocal
from app.models import RedditPost

logger = logging.getLogger(__name__)


def _create_reddit_client() -> praw.Reddit | None:
    """
    Create and return a PRAW Reddit client.
    Returns None if credentials are not configured.
    """
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        logger.error("Reddit credentials not set in .env — skipping Reddit fetch")
        return None

    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )


def fetch_reddit(
    tickers: list[str] | None = None,
    subreddits: list[str] | None = None,
    post_limit: int = 25,
    comment_limit: int = 5,
) -> dict:
    """
    Search Reddit for ticker mentions and store posts + comments.

    Args:
        tickers: List of stock symbols. Defaults to config.TICKERS.
        subreddits: Subreddit names to search. Defaults to config.SUBREDDITS.
        post_limit: Max posts to fetch per ticker per subreddit.
        comment_limit: Max top comments to store per post.

    Returns:
        dict: {ticker: number_of_items_stored} summary.
    """
    reddit = _create_reddit_client()
    if reddit is None:
        return {}

    tickers = tickers or TICKERS
    subreddits = subreddits or SUBREDDITS

    logger.info(
        f"Fetching Reddit data for {len(tickers)} tickers "
        f"across {len(subreddits)} subreddits"
    )

    results = {}
    db: Session = SessionLocal()

    try:
        for ticker in tickers:
            items_stored = 0

            for sub_name in subreddits:
                try:
                    subreddit = reddit.subreddit(sub_name)
                    logger.info(f"  Searching r/{sub_name} for ${ticker}...")

                    # Search for the ticker symbol (with $ prefix for financial context)
                    # Also search without $ for broader matches
                    search_query = f"${ticker} OR {ticker}"

                    for submission in subreddit.search(
                        search_query,
                        sort="new",
                        time_filter="week",  # last 7 days
                        limit=post_limit,
                    ):
                        # --- Store the post itself ---
                        post_id = submission.id

                        # Check if post already exists
                        existing = db.query(RedditPost).filter(
                            RedditPost.post_id == post_id,
                            RedditPost.ticker == ticker,
                        ).first()

                        if not existing:
                            post = RedditPost(
                                ticker=ticker,
                                post_id=post_id,
                                subreddit=sub_name,
                                title=submission.title[:1000] if submission.title else None,
                                body=(submission.selftext[:2000]
                                      if submission.selftext else None),
                                score=submission.score,
                                num_comments=submission.num_comments,
                                post_type="post",
                                created_utc=datetime.utcfromtimestamp(
                                    submission.created_utc
                                ),
                            )
                            db.add(post)
                            items_stored += 1

                        # --- Store top comments ---
                        submission.comment_sort = "best"
                        # Replace "MoreComments" objects with actual comments
                        submission.comments.replace_more(limit=0)

                        for comment in submission.comments[:comment_limit]:
                            comment_id = comment.id

                            existing_comment = db.query(RedditPost).filter(
                                RedditPost.post_id == comment_id,
                                RedditPost.ticker == ticker,
                            ).first()

                            if not existing_comment and comment.body:
                                reddit_comment = RedditPost(
                                    ticker=ticker,
                                    post_id=comment_id,
                                    subreddit=sub_name,
                                    title=None,
                                    body=comment.body[:2000],
                                    score=comment.score,
                                    num_comments=0,
                                    post_type="comment",
                                    created_utc=datetime.utcfromtimestamp(
                                        comment.created_utc
                                    ),
                                )
                                db.add(reddit_comment)
                                items_stored += 1

                    db.commit()

                except Exception as e:
                    logger.error(
                        f"  Error searching r/{sub_name} for {ticker}: {e}"
                    )
                    db.rollback()

            results[ticker] = items_stored
            logger.info(f"  {ticker}: {items_stored} Reddit items stored")

    finally:
        db.close()

    logger.info(f"Reddit fetch complete. Summary: {results}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_reddit()
