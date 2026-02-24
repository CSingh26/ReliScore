#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path

import duckdb

CANONICAL_COLUMNS: list[tuple[str, str, list[str]]] = [
    ("date", "DATE", ["date", "day"]),
    ("serial_number", "VARCHAR", ["serial_number", "serial"]),
    ("model", "VARCHAR", ["model", "model_name"]),
    ("failure", "INTEGER", ["failure", "is_failed_today"]),
    ("capacity_bytes", "BIGINT", ["capacity_bytes"]),
    ("smart_5_raw", "DOUBLE", ["smart_5_raw", "smart_5"]),
    ("smart_187_raw", "DOUBLE", ["smart_187_raw", "smart_187"]),
    ("smart_188_raw", "DOUBLE", ["smart_188_raw", "smart_188"]),
    ("smart_197_raw", "DOUBLE", ["smart_197_raw", "smart_197"]),
    ("smart_198_raw", "DOUBLE", ["smart_198_raw", "smart_198"]),
    ("smart_199_raw", "DOUBLE", ["smart_199_raw", "smart_199"]),
    ("smart_241_raw", "DOUBLE", ["smart_241_raw", "smart_241"]),
    ("smart_242_raw", "DOUBLE", ["smart_242_raw", "smart_242"]),
    ("temperature", "DOUBLE", ["temperature", "temperature_raw", "smart_194_raw", "smart_194"]),
]


def _quote(identifier: str) -> str:
    return f'"{identifier.replace("\"", "\"\"")}"'


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _column_names(conn: duckdb.DuckDBPyConnection, csv_path: Path) -> set[str]:
    query = "SELECT * FROM read_csv_auto(?, header=true, all_varchar=true, ignore_errors=true, sample_size=-1) LIMIT 0"
    relation = conn.execute(query, [str(csv_path)])
    return {description[0] for description in relation.description}


def _canonical_select_exprs(available_columns: set[str]) -> str:
    available_lookup = {name.lower(): name for name in available_columns}
    exprs: list[str] = []

    for canonical_name, sql_type, aliases in CANONICAL_COLUMNS:
        source_column = next(
            (available_lookup[alias.lower()] for alias in aliases if alias.lower() in available_lookup),
            None,
        )

        if source_column is None:
            exprs.append(f"NULL::{sql_type} AS {_quote(canonical_name)}")
            continue

        source_ref = _quote(source_column)
        if sql_type == "VARCHAR":
            exprs.append(f"NULLIF(TRIM({source_ref}), '') AS {_quote(canonical_name)}")
        elif sql_type == "DATE":
            exprs.append(
                f"TRY_CAST(NULLIF(TRIM({source_ref}), '') AS DATE) AS {_quote(canonical_name)}"
            )
        else:
            exprs.append(
                f"TRY_CAST(NULLIF(TRIM({source_ref}), '') AS {sql_type}) AS {_quote(canonical_name)}"
            )

    return ",\n      ".join(exprs)


def _ingest_csv(conn: duckdb.DuckDBPyConnection, csv_path: Path, out_dir: Path) -> None:
    available_columns = _column_names(conn, csv_path)
    select_exprs = _canonical_select_exprs(available_columns)
    csv_literal = _sql_literal(str(csv_path))
    out_literal = _sql_literal(str(out_dir))

    conn.execute(
        f"""
        COPY (
          WITH source AS (
            SELECT
              {select_exprs}
            FROM read_csv_auto({csv_literal}, header=true, all_varchar=true, ignore_errors=true, sample_size=-1)
          ), normalized AS (
            SELECT
              *,
              EXTRACT(YEAR FROM date) AS year,
              LPAD(CAST(EXTRACT(MONTH FROM date) AS VARCHAR), 2, '0') AS month
            FROM source
            WHERE date IS NOT NULL
              AND serial_number IS NOT NULL
          )
          SELECT * FROM normalized
        ) TO {out_literal} (
          FORMAT PARQUET,
          PARTITION_BY (year, month),
          OVERWRITE_OR_IGNORE TRUE,
          COMPRESSION ZSTD
        )
        """
    )


def _is_metadata_csv(path: Path) -> bool:
    if path.name.startswith("._"):
        return True
    return "__MACOSX" in path.parts


def build_warehouse(zips_dir: Path, out_dir: Path, max_csv_files: int | None = None) -> int:
    if not zips_dir.exists():
        raise FileNotFoundError(f"ZIP directory not found: {zips_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(database=":memory:")

    processed_csv_count = 0
    zip_paths = sorted(zips_dir.glob("*.zip"))
    if not zip_paths:
        raise RuntimeError(f"No ZIP files found in {zips_dir}")

    for zip_path in zip_paths:
        with tempfile.TemporaryDirectory(prefix="backblaze_extract_") as temp_dir:
            temp_root = Path(temp_dir)
            with zipfile.ZipFile(zip_path, "r") as archive:
                archive.extractall(temp_root)

            for csv_path in sorted(temp_root.rglob("*.csv")):
                if _is_metadata_csv(csv_path):
                    continue
                _ingest_csv(conn, csv_path, out_dir)
                processed_csv_count += 1
                if max_csv_files and processed_csv_count >= max_csv_files:
                    print(f"Reached --max_csv_files={max_csv_files}; stopping ingest")
                    conn.close()
                    return processed_csv_count

    conn.close()
    return processed_csv_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Backblaze local parquet warehouse")
    parser.add_argument("--zips", type=Path, default=Path("data/backblaze/zips"))
    parser.add_argument("--out", type=Path, default=Path("data/backblaze/warehouse"))
    parser.add_argument(
        "--max_csv_files",
        type=int,
        default=None,
        help="Limit CSV files for smoke runs",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove warehouse directory before rebuild",
    )
    args = parser.parse_args()

    if args.clean and args.out.exists():
        shutil.rmtree(args.out)

    count = build_warehouse(zips_dir=args.zips, out_dir=args.out, max_csv_files=args.max_csv_files)
    print(f"Warehouse build complete. Processed CSV files: {count}. Output: {args.out}")


if __name__ == "__main__":
    main()
