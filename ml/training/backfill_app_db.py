#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import requests
import duckdb
from psycopg.types.json import Json


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return bool(value)


def _resolve_latest_day(conn: duckdb.DuckDBPyConnection, parquet_glob: str) -> date:
    latest = conn.execute(
        "SELECT MAX(CAST(date AS DATE)) FROM read_parquet(?, union_by_name=true)",
        [parquet_glob],
    ).fetchone()[0]
    if latest is None:
        raise RuntimeError("Warehouse dataset is empty; cannot resolve latest date")
    return latest


def _prepare_selected_drives(
    conn: duckdb.DuckDBPyConnection,
    parquet_glob: str,
    latest_day: date,
    max_drives: int | None,
) -> int:
    limit_clause = f"LIMIT {max_drives}" if max_drives and max_drives > 0 else ""

    conn.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE selected_drives AS
        SELECT
          serial_number,
          COALESCE(ANY_VALUE(NULLIF(TRIM(model), '')), 'UNKNOWN') AS model,
          MAX(TRY_CAST(capacity_bytes AS BIGINT)) AS capacity_bytes
        FROM read_parquet(?, union_by_name=true)
        WHERE CAST(date AS DATE) = ?
          AND serial_number IS NOT NULL
        GROUP BY serial_number
        ORDER BY serial_number
        {limit_clause}
        """,
        [parquet_glob, latest_day],
    )

    return int(conn.execute("SELECT COUNT(*) FROM selected_drives").fetchone()[0])


def _telemetry_query() -> str:
    return """
      SELECT
        t.serial_number AS drive_id,
        CAST(t.date AS DATE) AS day,
        TRY_CAST(t.smart_5_raw AS BIGINT) AS smart5,
        TRY_CAST(t.smart_187_raw AS BIGINT) AS smart187,
        TRY_CAST(t.smart_188_raw AS BIGINT) AS smart188,
        TRY_CAST(t.smart_197_raw AS BIGINT) AS smart197,
        TRY_CAST(t.smart_198_raw AS BIGINT) AS smart198,
        TRY_CAST(t.smart_199_raw AS BIGINT) AS smart199,
        TRY_CAST(t.temperature AS DOUBLE) AS temperature,
        CASE WHEN TRY_CAST(t.failure AS INTEGER) = 1 THEN TRUE ELSE FALSE END AS is_failed_today,
        COALESCE(sd.model, NULLIF(TRIM(t.model), ''), 'UNKNOWN') AS model,
        COALESCE(sd.capacity_bytes, TRY_CAST(t.capacity_bytes AS BIGINT)) AS capacity_bytes
      FROM read_parquet(?, union_by_name=true) t
      INNER JOIN selected_drives sd
        ON t.serial_number = sd.serial_number
      WHERE t.serial_number IS NOT NULL
        AND CAST(t.date AS DATE) BETWEEN ? AND ?
      ORDER BY t.serial_number, CAST(t.date AS DATE)
    """


def _drive_summary_query() -> str:
    return """
      SELECT
        sd.serial_number AS drive_id,
        COALESCE(NULLIF(TRIM(sd.model), ''), 'UNKNOWN') AS model,
        sd.capacity_bytes AS capacity_bytes,
        MIN(CAST(t.date AS DATE)) AS first_seen,
        MAX(CAST(t.date AS DATE)) AS last_seen
      FROM selected_drives sd
      INNER JOIN read_parquet(?, union_by_name=true) t
        ON t.serial_number = sd.serial_number
      WHERE CAST(t.date AS DATE) BETWEEN ? AND ?
      GROUP BY sd.serial_number, sd.model, sd.capacity_bytes
      ORDER BY sd.serial_number
    """


def backfill(
    warehouse_dir: Path,
    database_url: str,
    lookback_days: int,
    max_drives: int | None,
    batch_size: int,
    clear_existing: bool,
    latest_day: date | None,
    score_url: str | None,
) -> None:
    parquet_glob = str(warehouse_dir / "**" / "*.parquet")
    conn = duckdb.connect(database=":memory:")

    resolved_latest_day = latest_day or _resolve_latest_day(conn, parquet_glob)
    start_day = resolved_latest_day - timedelta(days=lookback_days)
    selected_drive_count = _prepare_selected_drives(conn, parquet_glob, resolved_latest_day, max_drives)
    if selected_drive_count == 0:
        raise RuntimeError("No drives selected from latest day snapshot")

    drive_records: list[tuple[str, str, int | None, str, date, date]] = []
    for row in conn.execute(
        _drive_summary_query(),
        [parquet_glob, start_day, resolved_latest_day],
    ).fetchall():
        drive_id, model, capacity_bytes, first_seen, last_seen = row
        drive_records.append(
            (
                str(drive_id),
                str(model or "UNKNOWN"),
                _to_int(capacity_bytes),
                "backblaze",
                first_seen,
                last_seen,
            )
        )

    if not drive_records:
        raise RuntimeError("No drive records discovered in selected telemetry window")

    telemetry_inserted = 0

    with psycopg.connect(database_url) as pg_conn:
        with pg_conn.cursor() as cur:
            if clear_existing:
                cur.execute(
                    """
                    TRUNCATE TABLE predictions, features_daily, telemetry_daily, audit_log, drives
                    RESTART IDENTITY CASCADE
                    """
                )

            cur.executemany(
                """
                INSERT INTO drives (
                  drive_id,
                  model,
                  capacity_bytes,
                  datacenter,
                  first_seen,
                  last_seen
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (drive_id) DO UPDATE
                SET
                  model = EXCLUDED.model,
                  capacity_bytes = COALESCE(EXCLUDED.capacity_bytes, drives.capacity_bytes),
                  datacenter = EXCLUDED.datacenter,
                  first_seen = LEAST(drives.first_seen, EXCLUDED.first_seen),
                  last_seen = GREATEST(drives.last_seen, EXCLUDED.last_seen)
                """,
                drive_records,
            )

        with pg_conn.cursor() as cur:
            with cur.copy(
                """
                COPY telemetry_daily (
                  drive_id,
                  day,
                  smart_5,
                  smart_187,
                  smart_188,
                  smart_197,
                  smart_198,
                  smart_199,
                  temperature,
                  io_read_latency_ms,
                  io_write_latency_ms,
                  is_failed_today
                ) FROM STDIN
                """
            ) as copy:
                reader = conn.execute(
                    _telemetry_query(),
                    [parquet_glob, start_day, resolved_latest_day],
                ).fetch_record_batch(rows_per_batch=batch_size)

                for batch in reader:
                    for row in batch.to_pylist():
                        drive_id = str(row["drive_id"])

                        copy.write_row(
                            (
                                drive_id,
                                row["day"],
                                _to_int(row["smart5"]),
                                _to_int(row["smart187"]),
                                _to_int(row["smart188"]),
                                _to_int(row["smart197"]),
                                _to_int(row["smart198"]),
                                _to_int(row["smart199"]),
                                _to_float(row["temperature"]),
                                None,
                                None,
                                _to_bool(row["is_failed_today"]),
                            )
                        )
                        telemetry_inserted += 1

        with pg_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_log (id, action, payload)
                VALUES (
                  %s,
                  'INGESTION',
                  %s
                )
                """,
                [
                    str(uuid4()),
                    Json(
                        {
                            "source": "backblaze-warehouse",
                            "latest_day": resolved_latest_day.isoformat(),
                            "start_day": start_day.isoformat(),
                            "selected_drives": len(drive_records),
                            "inserted_telemetry_rows": telemetry_inserted,
                            "loaded_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                ],
            )

        pg_conn.commit()

    score_response = None
    if score_url:
        response = requests.post(
            score_url,
            json={"day": resolved_latest_day.isoformat()},
            timeout=600,
        )
        response.raise_for_status()
        score_response = response.json()

    print(
        "Backfill complete",
        {
            "latest_day": resolved_latest_day.isoformat(),
            "start_day": start_day.isoformat(),
            "selected_drives": len(drive_records),
            "inserted_telemetry_rows": telemetry_inserted,
            "score_result": score_response,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill app Postgres tables from Backblaze parquet warehouse"
    )
    parser.add_argument("--warehouse", type=Path, default=Path("data/backblaze/warehouse"))
    parser.add_argument(
        "--database-url",
        type=str,
        default="postgresql://reliscore:reliscore@localhost:5432/reliscore",
    )
    parser.add_argument("--lookback-days", type=int, default=45)
    parser.add_argument("--max-drives", type=int, default=5000)
    parser.add_argument("--batch-size", type=int, default=50_000)
    parser.add_argument("--latest-day", type=date.fromisoformat, default=None)
    parser.add_argument("--score-url", type=str, default=None)
    parser.add_argument("--no-clear-existing", action="store_true")
    args = parser.parse_args()

    if not args.warehouse.exists():
        raise FileNotFoundError(f"Warehouse directory not found: {args.warehouse}")

    max_drives = args.max_drives if args.max_drives and args.max_drives > 0 else None
    backfill(
        warehouse_dir=args.warehouse,
        database_url=args.database_url,
        lookback_days=args.lookback_days,
        max_drives=max_drives,
        batch_size=args.batch_size,
        clear_existing=not args.no_clear_existing,
        latest_day=args.latest_day,
        score_url=args.score_url,
    )


if __name__ == "__main__":
    main()
