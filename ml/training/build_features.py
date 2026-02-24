#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import duckdb

SMART_FEATURE_COLUMNS = [
    "smart_5_raw",
    "smart_187_raw",
    "smart_188_raw",
    "smart_197_raw",
    "smart_198_raw",
    "smart_199_raw",
    "smart_241_raw",
    "smart_242_raw",
    "temperature",
]


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _window_feature_exprs() -> str:
    expressions: list[str] = []
    for column in SMART_FEATURE_COLUMNS:
        expressions.extend(
            [
                f"AVG({column}) OVER w7 AS {column}_mean_7d",
                f"AVG({column}) OVER w30 AS {column}_mean_30d",
                f"STDDEV_POP({column}) OVER w30 AS {column}_std_30d",
                f"{column} - AVG({column}) OVER w7 AS {column}_delta_vs_7d",
                (
                    f"CASE WHEN {column} > LAG({column}) OVER "
                    f"(PARTITION BY serial_number ORDER BY as_of_date) THEN 1 ELSE 0 END "
                    f"AS {column}_is_increasing"
                ),
            ]
        )
    return ",\n      ".join(expressions)


def build_features(
    warehouse_dir: Path,
    out_dir: Path,
    horizon_days: int,
    row_limit: int | None,
) -> None:
    if not warehouse_dir.exists():
        raise FileNotFoundError(f"Warehouse not found: {warehouse_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(database=":memory:")

    feature_exprs = _window_feature_exprs()
    limit_clause = f"LIMIT {row_limit}" if row_limit and row_limit > 0 else ""
    warehouse_glob_literal = _sql_literal(str(warehouse_dir / "**" / "*.parquet"))
    out_literal = _sql_literal(str(out_dir))

    conn.execute(
        f"""
        COPY (
          WITH base AS (
            SELECT
              CAST(date AS DATE) AS as_of_date,
              serial_number,
              model,
              TRY_CAST(failure AS INTEGER) AS failure,
              TRY_CAST(capacity_bytes AS BIGINT) AS capacity_bytes,
              TRY_CAST(smart_5_raw AS DOUBLE) AS smart_5_raw,
              TRY_CAST(smart_187_raw AS DOUBLE) AS smart_187_raw,
              TRY_CAST(smart_188_raw AS DOUBLE) AS smart_188_raw,
              TRY_CAST(smart_197_raw AS DOUBLE) AS smart_197_raw,
              TRY_CAST(smart_198_raw AS DOUBLE) AS smart_198_raw,
              TRY_CAST(smart_199_raw AS DOUBLE) AS smart_199_raw,
              TRY_CAST(smart_241_raw AS DOUBLE) AS smart_241_raw,
              TRY_CAST(smart_242_raw AS DOUBLE) AS smart_242_raw,
              TRY_CAST(temperature AS DOUBLE) AS temperature
            FROM read_parquet({warehouse_glob_literal}, union_by_name=true)
            WHERE date IS NOT NULL
              AND serial_number IS NOT NULL
          ), enriched AS (
            SELECT
              *,
              MIN(as_of_date) OVER (PARTITION BY serial_number) AS first_seen_date,
              MIN(CASE WHEN failure = 1 THEN as_of_date END)
                OVER (PARTITION BY serial_number) AS failure_date,
              {feature_exprs}
            FROM base
            WINDOW
              w7 AS (PARTITION BY serial_number ORDER BY as_of_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),
              w30 AS (PARTITION BY serial_number ORDER BY as_of_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
          ), final AS (
            SELECT
              as_of_date,
              serial_number,
              model,
              capacity_bytes,
              DATE_DIFF('day', first_seen_date, as_of_date) AS age_days,
              CASE
                WHEN failure_date > as_of_date
                  AND failure_date <= as_of_date + INTERVAL '{horizon_days} day'
                THEN 1
                ELSE 0
              END AS label_30d,
              {', '.join([f'{column}_mean_7d' for column in SMART_FEATURE_COLUMNS])},
              {', '.join([f'{column}_mean_30d' for column in SMART_FEATURE_COLUMNS])},
              {', '.join([f'{column}_std_30d' for column in SMART_FEATURE_COLUMNS])},
              {', '.join([f'{column}_delta_vs_7d' for column in SMART_FEATURE_COLUMNS])},
              {', '.join([f'{column}_is_increasing' for column in SMART_FEATURE_COLUMNS])},
              EXTRACT(YEAR FROM as_of_date) AS year,
              LPAD(CAST(EXTRACT(MONTH FROM as_of_date) AS VARCHAR), 2, '0') AS month
            FROM enriched
            WHERE as_of_date IS NOT NULL
          )
          SELECT * FROM final
          {limit_clause}
        ) TO {out_literal} (
          FORMAT PARQUET,
          PARTITION_BY (year, month),
          OVERWRITE_OR_IGNORE TRUE,
          COMPRESSION ZSTD
        )
        """
    )

    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build H=30 feature dataset from Backblaze warehouse")
    parser.add_argument("--warehouse", type=Path, default=Path("data/backblaze/warehouse"))
    parser.add_argument("--out", type=Path, default=Path("data/backblaze/features_h30"))
    parser.add_argument("--horizon-days", type=int, default=30)
    parser.add_argument("--row-limit", type=int, default=None)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    if args.clean and args.out.exists():
        shutil.rmtree(args.out)

    build_features(
        warehouse_dir=args.warehouse,
        out_dir=args.out,
        horizon_days=args.horizon_days,
        row_limit=args.row_limit,
    )
    print(f"Feature build complete: {args.out}")


if __name__ == "__main__":
    main()
