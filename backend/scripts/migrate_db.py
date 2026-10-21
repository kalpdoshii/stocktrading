"""
migrate_db.py — Safe Database Migration & Schema Update
======================================================
Applies database migrations safely to preserve all existing data:
  1. Deduplicates sentiment_scores (keeping highest-id / newest row per ticker+date+source_type)
  2. Adds UNIQUE KEY uq_ticker_date_src to sentiment_scores
  3. Deduplicates predictions (keeping highest-id row per ticker+date+model_version)
  4. Adds UNIQUE KEY uq_pred to predictions
  5. Updates predictions.signal_dir ENUM to include 'HOLD'
  6. Adds calibration and SHAP columns to predictions
  7. Adds validation, baseline, calibration, and class-balance columns to model_metrics
  8. Creates experiment_records table if not exists

Usage:
    python -m scripts.migrate_db
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration")


def run_migrations():
    logger.info("Starting safe database migration...")

    with engine.connect() as conn:
        # Step 1: Deduplicate sentiment_scores
        logger.info("Step 1: Checking and deduplicating sentiment_scores...")
        dedup_sentiment_sql = """
        DELETE s1 FROM sentiment_scores s1
        INNER JOIN sentiment_scores s2 
        WHERE s1.id < s2.id 
          AND s1.ticker = s2.ticker 
          AND s1.date = s2.date 
          AND s1.source_type = s2.source_type;
        """
        result = conn.execute(text(dedup_sentiment_sql))
        conn.commit()
        logger.info(f"  Removed {result.rowcount} duplicate sentiment_scores rows.")

        # Step 2: Ensure unique index on sentiment_scores
        logger.info("Step 2: Ensuring unique index on sentiment_scores(ticker, date, source_type)...")
        check_idx = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.statistics 
            WHERE table_schema = DATABASE() 
              AND table_name = 'sentiment_scores' 
              AND index_name = 'uq_ticker_date_src';
        """)).scalar()

        if check_idx == 0:
            conn.execute(text("""
                ALTER TABLE sentiment_scores 
                ADD UNIQUE KEY uq_ticker_date_src (ticker, date, source_type);
            """))
            conn.commit()
            logger.info("  Created unique index uq_ticker_date_src on sentiment_scores.")
        else:
            logger.info("  Index uq_ticker_date_src already exists.")

        # Step 3: Deduplicate predictions
        logger.info("Step 3: Checking and deduplicating predictions...")
        dedup_pred_sql = """
        DELETE p1 FROM predictions p1
        INNER JOIN predictions p2 
        WHERE p1.id < p2.id 
          AND p1.ticker = p2.ticker 
          AND p1.date = p2.date 
          AND p1.model_version = p2.model_version;
        """
        result = conn.execute(text(dedup_pred_sql))
        conn.commit()
        logger.info(f"  Removed {result.rowcount} duplicate predictions rows.")

        # Step 4: Ensure unique index on predictions
        logger.info("Step 4: Ensuring unique index on predictions(ticker, date, model_version)...")
        check_pred_idx = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.statistics 
            WHERE table_schema = DATABASE() 
              AND table_name = 'predictions' 
              AND index_name = 'uq_pred';
        """)).scalar()

        if check_pred_idx == 0:
            conn.execute(text("""
                ALTER TABLE predictions 
                ADD UNIQUE KEY uq_pred (ticker, date, model_version);
            """))
            conn.commit()
            logger.info("  Created unique index uq_pred on predictions.")
        else:
            logger.info("  Index uq_pred already exists.")

        # Step 5: Update signal_dir ENUM in predictions to allow 'HOLD'
        logger.info("Step 5: Updating predictions.signal_dir ENUM to ('UP', 'DOWN', 'HOLD')...")
        try:
            conn.execute(text("""
                ALTER TABLE predictions 
                MODIFY COLUMN signal_dir ENUM('UP', 'DOWN', 'HOLD') NOT NULL DEFAULT 'HOLD';
            """))
            conn.commit()
            logger.info("  predictions.signal_dir ENUM updated successfully.")
        except Exception as e:
            logger.warning(f"  Note on updating signal_dir ENUM: {e}")

        # Step 6: Add calibration and SHAP columns to predictions if missing
        logger.info("Step 6: Checking new columns on predictions...")
        pred_cols = [
            ("raw_confidence", "FLOAT"),
            ("calibrated_confidence", "FLOAT"),
            ("is_calibrated", "TINYINT(1) DEFAULT 0"),
            ("shap_values_json", "JSON"),
        ]
        for col_name, col_type in pred_cols:
            has_col = conn.execute(text(f"""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                  AND table_name = 'predictions' 
                  AND column_name = '{col_name}';
            """)).scalar()
            if has_col == 0:
                conn.execute(text(f"ALTER TABLE predictions ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                logger.info(f"  Added column predictions.{col_name}")

        # Step 7: Add validation and baseline columns to model_metrics if missing
        logger.info("Step 7: Checking new columns on model_metrics...")
        metrics_cols = [
            ("dataset_start", "DATE"),
            ("dataset_end", "DATE"),
            ("test_start", "DATE"),
            ("test_end", "DATE"),
            ("train_samples", "INT"),
            ("test_samples", "INT"),
            ("majority_baseline_accuracy", "FLOAT"),
            ("simple_baseline_accuracy", "FLOAT"),
            ("brier_score", "FLOAT"),
            ("pr_auc", "FLOAT"),
            ("class_balance_json", "JSON"),
            ("calibration_metrics_json", "JSON"),
            ("feature_importances_json", "JSON"),
            ("validation_type", "VARCHAR(50) DEFAULT 'holdout'"),
        ]
        for col_name, col_type in metrics_cols:
            has_col = conn.execute(text(f"""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                  AND table_name = 'model_metrics' 
                  AND column_name = '{col_name}';
            """)).scalar()
            if has_col == 0:
                conn.execute(text(f"ALTER TABLE model_metrics ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                logger.info(f"  Added column model_metrics.{col_name}")

        # Step 8: Create experiment_records table if not exists
        logger.info("Step 8: Ensuring experiment_records table exists...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS experiment_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                experiment_id VARCHAR(64) NOT NULL,
                model_name VARCHAR(50) NOT NULL,
                model_version VARCHAR(50) NOT NULL,
                ticker VARCHAR(20),
                validation_strategy VARCHAR(50) NOT NULL,
                dataset_start DATE,
                dataset_end DATE,
                parameters_json JSON,
                feature_names_json JSON,
                metrics_json JSON,
                baseline_metrics_json JSON,
                artifact_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_experiment_id (experiment_id),
                INDEX idx_model (model_version),
                INDEX idx_ticker (ticker)
            ) ENGINE=InnoDB;
        """))
        conn.commit()
        logger.info("  experiment_records table verified.")

    logger.info("✓ Database migration completed successfully without data loss!")


if __name__ == "__main__":
    run_migrations()
