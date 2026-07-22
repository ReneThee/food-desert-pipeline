"""One-command rebuild: raw files -> schema -> load -> views -> checks"""
import logging
import os
import subprocess
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("pipeline")

DB = "fooddesert"


def run_sql_file(path: str) -> None:
    log.info("Applying %s ...", path)
    result = subprocess.run(["psql", "-d", DB, "-v", "ON_ERROR_STOP=1", "-f", path],
                            capture_output=True, text=True)
    if result.returncode != 0:
        log.error("psql failed:\n%s", result.stderr)
        sys.exit(1)


def quality_checks(engine) -> None:
    checks = {
        "tracts loaded": "SELECT COUNT(*) FROM tracts",
        "no orphan demographics":
            "SELECT COUNT(*) FROM demographics d "
            "LEFT JOIN tracts t USING (geoid) WHERE t.geoid IS NULL",
        "scores computable": "SELECT COUNT(*) FROM food_desert_tracts",
        "score in range":
            "SELECT COUNT(*) FROM food_desert_score "
            "WHERE composite_score < 0 OR composite_score > 100",
    }
    with engine.connect() as conn:
        for name, sql in checks.items():
            val = conn.execute(text(sql)).scalar()
            log.info("CHECK | %-25s -> %s", name, val)
    log.info("Expected: tracts ~170, orphans 0, scores ~170, out-of-range 0")


if __name__ == "__main__":
    run_sql_file("sql/schema.sql")          # 1. reset structure

    log.info("Running ETL ...")
    from src.etl import load                # 2. transform + load
    engine = create_engine(os.environ["DATABASE_URL"])
    load(engine)

    run_sql_file("sql/views.sql")           # 3. derived layer
    quality_checks(engine)                  # 4. gate
    log.info("Pipeline complete.")