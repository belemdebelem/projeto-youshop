from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_bronze(
    source_name: str,
    source_path: Path,
    df_valid: pd.DataFrame,
    df_rejects: pd.DataFrame,
    run_id: str,
    bronze_dir: Path,
) -> dict:
    run_dir = bronze_dir / run_id / source_name
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_copy = run_dir / source_path.name
    shutil.copy2(source_path, raw_copy)
    if not df_valid.empty:
        df_valid.to_parquet(run_dir / "valid.parquet", index=False)
    if not df_rejects.empty:
        df_rejects.to_parquet(run_dir / "rejects.parquet", index=False)
    manifest = {
        "run_id": run_id,
        "source_name": source_name,
        "file_path": str(raw_copy),
        "file_hash": file_hash(source_path),
        "rows_read": int(len(df_valid) + len(df_rejects)),
        "rows_valid": int(len(df_valid)),
        "rows_rejected": int(len(df_rejects)),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest
