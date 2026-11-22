from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


class DuckDBRepo:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path))

    def init_schema(self) -> None:
        con = self.connect()
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_runs (
                    run_id VARCHAR PRIMARY KEY,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    status VARCHAR,
                    rules_version VARCHAR,
                    model_version VARCHAR,
                    config_hash VARCHAR,
                    summary_json VARCHAR
                );
                CREATE TABLE IF NOT EXISTS audit_file_manifest (
                    run_id VARCHAR,
                    source_name VARCHAR,
                    file_path VARCHAR,
                    file_hash VARCHAR,
                    rows_read BIGINT,
                    rows_valid BIGINT,
                    rows_rejected BIGINT,
                    ingested_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS audit_errors (
                    run_id VARCHAR,
                    stage VARCHAR,
                    entity_type VARCHAR,
                    entity_id VARCHAR,
                    severity VARCHAR,
                    message VARCHAR,
                    context_json VARCHAR,
                    created_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS audit_model_runs (
                    run_id VARCHAR,
                    model_name VARCHAR,
                    model_version VARCHAR,
                    params_json VARCHAR,
                    features_json VARCHAR,
                    dataset_hash VARCHAR,
                    metrics_json VARCHAR,
                    created_at TIMESTAMP
                );
                """
            )
        finally:
            con.close()

    def register_df(self, con: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame) -> None:
        con.register(name, df)

    def write_df(self, table: str, df: pd.DataFrame, mode: str = "append") -> None:
        con = self.connect()
        try:
            self.register_df(con, "df_tmp", df)
            if mode == "replace":
                con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM df_tmp")
            else:
                con.execute(f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM df_tmp WHERE 1=0")
                con.execute(f"INSERT INTO {table} SELECT * FROM df_tmp")
        finally:
            con.close()

    def query_df(self, sql: str, params: list | None = None) -> pd.DataFrame:
        con = self.connect()
        try:
            return con.execute(sql, params or []).df()
        finally:
            con.close()

    def execute(self, sql: str, params: list | None = None) -> None:
        con = self.connect()
        try:
            con.execute(sql, params or [])
        finally:
            con.close()
