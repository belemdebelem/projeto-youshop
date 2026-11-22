from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pandas as pd


def _record_hash(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    def h(row: pd.Series) -> str:
        payload = "|".join(str(row.get(c, "")) for c in cols)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return df.apply(h, axis=1)


def normalize_raw(source: str, df: pd.DataFrame, run_id: str) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if "amount" in col or "fee" in col or "net" in col or col == "commission_rate":
            out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in out.columns:
        if "date" in col:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.date.astype("string")
    out["source_name"] = source
    out["ingested_run_id"] = run_id
    out["normalized_at"] = datetime.now(timezone.utc).isoformat()
    hash_cols = [c for c in out.columns if c not in {"ingested_run_id", "normalized_at"}]
    out["record_hash"] = _record_hash(out, hash_cols)
    out = out.drop_duplicates(subset=["record_hash"]).reset_index(drop=True)
    return out
