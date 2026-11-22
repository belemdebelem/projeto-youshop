from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from youshop_finance.config import get_settings
from youshop_finance.ingestion.bronze_writer import write_bronze
from youshop_finance.ingestion.reader import read_table
from youshop_finance.ingestion.validator import validate_raw
from youshop_finance.intelligence.priority import build_priority
from youshop_finance.intelligence.scoring import build_anomaly_scores
from youshop_finance.logging import setup_logging
from youshop_finance.reconciliation.engine import ReconConfig, reconcile
from youshop_finance.reporting.explanations import build_case_briefs
from youshop_finance.reporting.exporters import export_reports
from youshop_finance.storage.duckdb_repo import DuckDBRepo
from youshop_finance.transform.silver import normalize_raw


RAW_FILES = {
    "sales": "sales.csv",
    "gateway_payments": "gateway_payments.csv",
    "commissions": "commissions.csv",
    "producer_receivables": "producer_receivables.csv",
    "payouts": "payouts.csv",
    "refunds_chargebacks": "refunds_chargebacks.csv",
}


def _config_hash() -> str:
    s = get_settings()
    payload = {
        "amount_tolerance": s.amount_tolerance,
        "payout_match_window_days": s.payout_match_window_days,
        "anomaly_contamination": s.anomaly_contamination,
        "weights": [s.priority_w_financial, s.priority_w_anomaly, s.priority_w_urgency],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def run_pipeline(run_id: str | None = None) -> str:
    settings = get_settings()
    logger = setup_logging()
    repo = DuckDBRepo(settings.duckdb_path)
    repo.init_schema()
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    started_at = datetime.now(timezone.utc).isoformat()
    repo.execute("DELETE FROM audit_runs WHERE run_id = ?", [run_id])
    repo.execute(
        "INSERT INTO audit_runs(run_id, started_at, status, rules_version, model_version, config_hash, summary_json) VALUES (?,?,?,?,?,?,?)",
        [run_id, started_at, "running", "R1-R6-v1", "MAD-IQR+IF-v1", _config_hash(), "{}"],
    )

    manifests = []
    all_rejects = []
    silver_counts = {}
    for source, filename in RAW_FILES.items():
        path = settings.data_raw_dir / filename
        if not path.exists():
            logger.warning("Missing raw file: %s", path)
            continue
        df_raw = read_table(path)
        df_valid, df_rejects = validate_raw(source, df_raw)
        manifest = write_bronze(source, path, df_valid, df_rejects, run_id, settings.data_bronze_dir)
        manifests.append(manifest)

        if not df_valid.empty:
            silver = normalize_raw(source, df_valid, run_id)
            table = f"silver_{source}"
            exists = repo.query_df(
                "SELECT table_name FROM information_schema.tables WHERE table_name=?",
                [table],
            ).shape[0] > 0
            if exists:
                repo.execute(f"DELETE FROM {table} WHERE ingested_run_id = ?", [run_id])
            repo.write_df(table, silver, mode="append")
            silver_counts[source] = len(silver)
        else:
            silver_counts[source] = 0

        if not df_rejects.empty:
            rej = df_rejects.copy()
            rej["source_name"] = source
            rej["run_id"] = run_id
            rej["rejected_at"] = datetime.now(timezone.utc).isoformat()
            all_rejects.append(rej)

    if manifests:
        mdf = pd.DataFrame(manifests)
        mdf["ingested_at"] = pd.to_datetime(mdf["ingested_at"])
        repo.execute("DELETE FROM audit_file_manifest WHERE run_id = ?", [run_id])
        repo.write_df("audit_file_manifest", mdf, mode="append")
    if all_rejects:
        rdf = pd.concat(all_rejects, ignore_index=True)
        exists = repo.query_df(
            "SELECT table_name FROM information_schema.tables WHERE table_name=?",
            ["silver_rejects"],
        ).shape[0] > 0
        if exists:
            repo.execute("DELETE FROM silver_rejects WHERE run_id = ?", [run_id])
        repo.write_df("silver_rejects", rdf, mode="append")

    # Reconciliation on current run silver
    silver = {}
    for source in RAW_FILES:
        table = f"silver_{source}"
        exists = repo.query_df("SELECT table_name FROM information_schema.tables WHERE table_name=?", [table]).shape[0] > 0
        silver[source] = repo.query_df(f"SELECT * FROM {table} WHERE ingested_run_id = ?", [run_id]) if exists else pd.DataFrame()

    recon_df = reconcile(run_id, silver, ReconConfig(amount_tolerance=settings.amount_tolerance, payout_match_window_days=settings.payout_match_window_days))
    anomaly_df, anomaly_meta = build_anomaly_scores(run_id, silver, contamination=settings.anomaly_contamination)
    if not anomaly_df.empty:
        repo.execute("DELETE FROM gold_anomaly_scores WHERE run_id = ?", [run_id]) if repo.query_df("SELECT table_name FROM information_schema.tables WHERE table_name='gold_anomaly_scores'").shape[0] > 0 else None
        repo.write_df("gold_anomaly_scores", anomaly_df, mode="append")
        repo.execute("DELETE FROM audit_model_runs WHERE run_id = ? AND model_name = ?", [run_id, anomaly_meta["model_name"]]) if repo.query_df("SELECT table_name FROM information_schema.tables WHERE table_name='audit_model_runs'").shape[0] > 0 else None
        repo.write_df("audit_model_runs", pd.DataFrame([{
            "run_id": run_id,
            "model_name": anomaly_meta["model_name"],
            "model_version": anomaly_meta["model_version"],
            "params_json": json.dumps(anomaly_meta["params"], ensure_ascii=False),
            "features_json": json.dumps(anomaly_meta["features"], ensure_ascii=False),
            "dataset_hash": _config_hash(),
            "metrics_json": json.dumps({"rows_scored": anomaly_meta["rows"]}, ensure_ascii=False),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }]), mode="append")

    if not recon_df.empty:
        repo.execute("DELETE FROM gold_reconciliation_cases WHERE run_id = ?", [run_id]) if repo.query_df("SELECT table_name FROM information_schema.tables WHERE table_name='gold_reconciliation_cases'").shape[0] > 0 else None
        repo.write_df("gold_reconciliation_cases", recon_df, mode="append")
        div = recon_df[recon_df["reconciliation_status"] != "matched"].copy()
        repo.execute("DELETE FROM gold_divergences WHERE run_id = ?", [run_id]) if repo.query_df("SELECT table_name FROM information_schema.tables WHERE table_name='gold_divergences'").shape[0] > 0 else None
        if not div.empty:
            repo.write_df("gold_divergences", div, mode="append")

    priority_df = build_priority(run_id, recon_df, anomaly_df, (settings.priority_w_financial, settings.priority_w_anomaly, settings.priority_w_urgency))
    if not priority_df.empty:
        repo.execute("DELETE FROM gold_case_priority WHERE run_id = ?", [run_id]) if repo.query_df("SELECT table_name FROM information_schema.tables WHERE table_name='gold_case_priority'").shape[0] > 0 else None
        repo.write_df("gold_case_priority", priority_df, mode="append")

    briefs_df = build_case_briefs(run_id, recon_df)
    if not briefs_df.empty:
        repo.execute("DELETE FROM gold_case_briefs WHERE run_id = ?", [run_id]) if repo.query_df("SELECT table_name FROM information_schema.tables WHERE table_name='gold_case_briefs'").shape[0] > 0 else None
        repo.write_df("gold_case_briefs", briefs_df, mode="append")

    exports = export_reports(run_id, settings.data_exports_dir, {
        "reconciliation_cases": recon_df,
        "divergences": recon_df[recon_df["reconciliation_status"] != "matched"].copy() if not recon_df.empty else pd.DataFrame(),
        "anomaly_scores": anomaly_df,
        "case_priority": priority_df,
        "case_briefs": briefs_df,
    })

    summary = {
        "run_id": run_id,
        "silver_counts": silver_counts,
        "manifest_count": len(manifests),
        "recon_cases": int(len(recon_df)),
        "recon_divergences": int((recon_df["reconciliation_status"] != "matched").sum()) if not recon_df.empty else 0,
        "anomalies_scored": int(len(anomaly_df)),
        "anomalies_flagged": int(anomaly_df["is_anomaly"].sum()) if not anomaly_df.empty else 0,
        "priority_cases": int(len(priority_df)),
        "briefs": int(len(briefs_df)),
        "exports": exports,
    }
    repo.execute(
        "UPDATE audit_runs SET ended_at=?, status=?, summary_json=? WHERE run_id=?",
        [datetime.now(timezone.utc).isoformat(), "reconciled", json.dumps(summary, ensure_ascii=False), run_id],
    )
    logger.info("Pipeline complete: %s", summary)
    return run_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    run_pipeline(args.run_id)
