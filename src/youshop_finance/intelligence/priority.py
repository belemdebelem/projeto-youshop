from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd


SEVERITY_MAP = {"low": 0.1, "medium": 0.35, "high": 0.7, "critical": 1.0}


def build_priority(run_id: str, recon: pd.DataFrame, anomalies: pd.DataFrame, weights: tuple[float, float, float]) -> pd.DataFrame:
    if recon.empty:
        return pd.DataFrame()
    wf, wa, wu = weights
    total = wf + wa + wu
    wf, wa, wu = wf / total, wa / total, wu / total

    anom_by_sale = {}
    if not anomalies.empty:
        for _, a in anomalies.iterrows():
            anom_by_sale[str(a.get("entity_id"))] = float(a.get("anomaly_score", 0.0))

    rows = []
    for _, c in recon.iterrows():
        if c.get("reconciliation_status") == "matched":
            continue
        sev = SEVERITY_MAP.get(str(c.get("severity", "low")).lower(), 0.2)
        # link anomaly by sale id in entity_a or entity_b
        sale_id = None
        for col in ["entity_a_id", "entity_b_id"]:
            val = str(c.get(col) or "")
            if val.startswith("SAL_"):
                sale_id = val
                break
        anom_score = anom_by_sale.get(sale_id, 0.0)
        # urgency: higher for critical/high and missing/duplicate/orphan
        status = str(c.get("reconciliation_status", ""))
        urgency = 0.5
        if status in {"duplicate_payment", "orphan_event"}:
            urgency = 1.0
        elif status in {"missing_payment", "missing_payout", "amount_mismatch", "commission_mismatch"}:
            urgency = 0.8
        elif status in {"pending_payout"}:
            urgency = 0.6
        priority = (wf * sev) + (wa * anom_score) + (wu * urgency)
        if status in {"duplicate_payment", "orphan_event"} and sev >= 1.0:
            priority = max(priority, 0.95)
        rows.append({
            "case_id": c.get("case_id"),
            "run_id": run_id,
            "financial_severity": round(sev, 4),
            "anomaly_score": round(float(anom_score), 6),
            "urgency_score": round(float(urgency), 4),
            "priority_score": round(float(priority), 6),
            "priority_reason": json.dumps({
                "reconciliation_status": status,
                "severity": c.get("severity"),
                "sale_id": sale_id,
                "weights": {"financial": wf, "anomaly": wa, "urgency": wu},
            }, ensure_ascii=False),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return pd.DataFrame(rows)
