from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def _robust_z(series: pd.Series) -> pd.Series:
    med = series.median()
    mad = (series - med).abs().median()
    if mad == 0 or pd.isna(mad):
        std = series.std(ddof=0)
        if std == 0 or pd.isna(std):
            return pd.Series(np.zeros(len(series)), index=series.index)
        return (series - series.mean()) / std
    return 0.6745 * (series - med) / mad


def build_anomaly_scores(run_id: str, silver: dict[str, pd.DataFrame], contamination: float = 0.05) -> tuple[pd.DataFrame, dict]:
    sales = silver.get("sales", pd.DataFrame()).copy()
    if sales.empty:
        return pd.DataFrame(), {"model": "IsolationForest", "rows": 0}

    feat = sales[["sale_id", "producer_id", "creator_id", "gross_amount", "net_amount", "platform_fee"]].copy()
    feat["gross_amount"] = pd.to_numeric(feat["gross_amount"], errors="coerce").fillna(0.0)
    feat["net_amount"] = pd.to_numeric(feat["net_amount"], errors="coerce").fillna(0.0)
    feat["platform_fee"] = pd.to_numeric(feat["platform_fee"], errors="coerce").fillna(0.0)
    feat["fee_rate"] = np.where(feat["gross_amount"] > 0, feat["platform_fee"] / feat["gross_amount"], 0.0)

    for col in ["gross_amount", "fee_rate"]:
        grp_med = feat.groupby("producer_id")[col].transform("median")
        grp_mad = feat.groupby("producer_id")[col].transform(lambda s: (s - s.median()).abs().median())
        feat[f"{col}_vs_med"] = feat[col] - grp_med
        feat[f"{col}_robust_z"] = np.where(grp_mad > 0, 0.6745 * (feat[col] - grp_med) / grp_mad, 0.0)

    model_features = ["gross_amount", "net_amount", "fee_rate", "gross_amount_vs_med", "gross_amount_robust_z", "fee_rate_robust_z"]
    X = feat[model_features].fillna(0.0).to_numpy()

    model = IsolationForest(n_estimators=200, contamination=min(max(contamination, 0.01), 0.2), random_state=42)
    model.fit(X)
    raw = -model.score_samples(X)  # higher = more anomalous
    pmin, pmax = float(raw.min()), float(raw.max())
    norm = (raw - pmin) / (pmax - pmin) if pmax > pmin else np.zeros_like(raw)
    z = _robust_z(pd.Series(feat["gross_amount"]))

    rows = []
    for i, r in feat.reset_index(drop=True).iterrows():
        reasons = []
        if abs(float(r["gross_amount_robust_z"])) >= 3.5:
            reasons.append("gross_amount_outlier_group")
        if abs(float(r["fee_rate_robust_z"])) >= 3.5:
            reasons.append("fee_rate_outlier_group")
        if abs(float(z.iloc[i])) >= 3.5 and "gross_amount_outlier_global" not in reasons:
            reasons.append("gross_amount_outlier_global")
        score = float(norm[i])
        is_anom = score >= 0.80 or len(reasons) > 0
        rows.append({
            "anomaly_id": f"{run_id}:sale:{r['sale_id']}",
            "run_id": run_id,
            "entity_type": "sale",
            "entity_id": r["sale_id"],
            "model_name": "IsolationForest",
            "model_version": "iforest-v1",
            "anomaly_score": round(score, 6),
            "baseline_context_json": json.dumps({"gross_amount_global_median": float(feat['gross_amount'].median()), "gross_amount_robust_z_global": float(z.iloc[i])}, ensure_ascii=False),
            "is_anomaly": bool(is_anom),
            "reason_codes": json.dumps(reasons, ensure_ascii=False),
            "feature_snapshot_json": json.dumps({k: (float(r[k]) if isinstance(r[k], (int, float, np.floating)) else r[k]) for k in model_features}, ensure_ascii=False),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    meta = {
        "model_name": "IsolationForest",
        "model_version": "iforest-v1",
        "params": {"n_estimators": 200, "contamination": min(max(contamination, 0.01), 0.2), "random_state": 42},
        "features": model_features,
        "rows": len(rows),
    }
    return pd.DataFrame(rows), meta
