from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd


@dataclass
class ReconConfig:
    amount_tolerance: float = 0.01
    payout_match_window_days: int = 3


def _case(
    run_id: str,
    case_type: str,
    a_type: str,
    a_id: str | None,
    b_type: str | None,
    b_id: str | None,
    expected: float | None,
    actual: float | None,
    status: str,
    rule: str,
    confidence: float,
    evidence: dict,
    severity: str = "low",
) -> dict:
    diff = None
    if expected is not None and actual is not None:
        diff = round(float(actual) - float(expected), 2)
    return {
        "case_id": f"{run_id}:{case_type}:{rule}:{a_type}:{a_id}:{b_type}:{b_id}:{status}",
        "run_id": run_id,
        "case_type": case_type,
        "entity_a_type": a_type,
        "entity_a_id": a_id,
        "entity_b_type": b_type,
        "entity_b_id": b_id,
        "expected_amount": expected,
        "actual_amount": actual,
        "diff_amount": diff,
        "reconciliation_status": status,
        "match_rule": rule,
        "confidence": confidence,
        "severity": severity,
        "evidence_json": json.dumps(evidence, ensure_ascii=False),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def reconcile(run_id: str, silver: dict[str, pd.DataFrame], cfg: ReconConfig) -> pd.DataFrame:
    sales = silver.get("sales", pd.DataFrame()).copy()
    payments = silver.get("gateway_payments", pd.DataFrame()).copy()
    commissions = silver.get("commissions", pd.DataFrame()).copy()
    payouts = silver.get("payouts", pd.DataFrame()).copy()
    refunds = silver.get("refunds_chargebacks", pd.DataFrame()).copy()

    cases: list[dict] = []
    tol = cfg.amount_tolerance

    # R1 sale x payment
    pay_by_sale = payments.groupby("sale_id") if not payments.empty else None
    for _, s in sales.iterrows():
        sid = s.get("sale_id")
        s_amt = float(s.get("gross_amount", 0) or 0)
        matches = payments[payments["sale_id"] == sid] if not payments.empty else pd.DataFrame()
        if matches.empty:
            cases.append(_case(run_id, "sale_payment", "sale", sid, "gateway_payment", None, s_amt, None, "missing_payment", "R1", 1.0, {"reason": "no payment for sale"}, "high"))
            continue
        if len(matches) > 1:
            for _, p in matches.iloc[1:].iterrows():
                cases.append(_case(run_id, "sale_payment", "sale", sid, "gateway_payment", p.get("payment_id"), s_amt, float(p.get("amount_captured", 0) or 0), "duplicate_payment", "R1", 1.0, {"reason": "multiple payments for same sale"}, "critical"))
        p = matches.iloc[0]
        p_amt = float(p.get("amount_captured", 0) or 0)
        diff = round(p_amt - s_amt, 2)
        if abs(diff) <= tol:
            cases.append(_case(run_id, "sale_payment", "sale", sid, "gateway_payment", p.get("payment_id"), s_amt, p_amt, "matched", "R1", 1.0, {"diff": diff}, "low"))
        else:
            sev = "high" if abs(diff) >= 50 else "medium"
            cases.append(_case(run_id, "sale_payment", "sale", sid, "gateway_payment", p.get("payment_id"), s_amt, p_amt, "amount_mismatch", "R1", 1.0, {"diff": diff}, sev))

    if not payments.empty:
        for _, p in payments.iterrows():
            if sales.empty or p.get("sale_id") not in set(sales["sale_id"]):
                cases.append(_case(run_id, "sale_payment", "gateway_payment", p.get("payment_id"), "sale", p.get("sale_id"), None, float(p.get("amount_captured", 0) or 0), "missing_sale", "R1", 1.0, {"reason": "payment without sale"}, "medium"))

    # R2 commission
    for _, c in commissions.iterrows():
        sid = c.get("sale_id")
        sale = sales[sales["sale_id"] == sid]
        if sale.empty:
            cases.append(_case(run_id, "commission", "commission", c.get("commission_id"), "sale", sid, None, float(c.get("expected_commission", 0) or 0), "missing_sale", "R2", 1.0, {"reason": "commission without sale"}, "medium"))
            continue
        s = sale.iloc[0]
        expected = round(float(s.get("gross_amount", 0) or 0) * float(c.get("commission_rate", 0) or 0), 2)
        actual = float(c.get("expected_commission", 0) or 0)
        diff = round(actual - expected, 2)
        if abs(diff) <= tol:
            cases.append(_case(run_id, "commission", "commission", c.get("commission_id"), "sale", sid, expected, actual, "matched", "R2", 1.0, {"diff": diff}, "low"))
        else:
            sev = "high" if abs(diff) >= 20 else "medium"
            cases.append(_case(run_id, "commission", "commission", c.get("commission_id"), "sale", sid, expected, actual, "commission_mismatch", "R2", 1.0, {"diff": diff, "expected_formula": "gross_amount*commission_rate"}, sev))

    # R3 payouts vs expected (creator commission + producer receivable)
    expected_payouts = []
    for _, c in commissions.iterrows():
        expected_payouts.append({
            "beneficiary_type": "creator", "beneficiary_id": c.get("creator_id"), "reference_id": c.get("sale_id"), "amount_due": float(c.get("expected_commission", 0) or 0), "source_type": "commission", "source_id": c.get("commission_id")
        })
    for _, s in sales.iterrows():
        expected_payouts.append({
            "beneficiary_type": "producer", "beneficiary_id": s.get("producer_id"), "reference_id": s.get("sale_id"), "amount_due": float(s.get("net_amount", 0) or 0), "source_type": "sale", "source_id": s.get("sale_id")
        })
    exp_df = pd.DataFrame(expected_payouts)
    used_payouts: set[str] = set()
    for _, e in exp_df.iterrows():
        cand = payouts[(payouts["beneficiary_type"] == e["beneficiary_type"]) & (payouts["beneficiary_id"] == e["beneficiary_id"]) & (payouts["reference_id"] == e["reference_id"])] if not payouts.empty else pd.DataFrame()
        cand = cand[~cand["payout_id"].isin(used_payouts)] if not cand.empty else cand
        if cand.empty:
            cases.append(_case(run_id, "payout", e["source_type"], e["source_id"], "payout", None, float(e["amount_due"]), None, "missing_payout", "R3", 1.0, {"beneficiary_type": e["beneficiary_type"], "beneficiary_id": e["beneficiary_id"], "reference_id": e["reference_id"]}, "high"))
            continue
        p = cand.iloc[0]
        used_payouts.add(p.get("payout_id"))
        p_amt = float(p.get("amount_paid", 0) or 0)
        diff = round(p_amt - float(e["amount_due"]), 2)
        if abs(diff) <= tol:
            cases.append(_case(run_id, "payout", e["source_type"], e["source_id"], "payout", p.get("payout_id"), float(e["amount_due"]), p_amt, "matched", "R3", 1.0, {"diff": diff}, "low"))
        else:
            cases.append(_case(run_id, "payout", e["source_type"], e["source_id"], "payout", p.get("payout_id"), float(e["amount_due"]), p_amt, "amount_mismatch", "R3", 1.0, {"diff": diff}, "high"))
        for _, extra in cand.iloc[1:].iterrows():
            used_payouts.add(extra.get("payout_id"))
            cases.append(_case(run_id, "payout", e["source_type"], e["source_id"], "payout", extra.get("payout_id"), float(e["amount_due"]), float(extra.get("amount_paid", 0) or 0), "duplicate_payout", "R3", 1.0, {"reason": "extra payout for same reference"}, "critical"))

    # R4 refunds/chargebacks
    for _, r in refunds.iterrows():
        sid = r.get("sale_id")
        sale = sales[sales["sale_id"] == sid]
        amt = float(r.get("amount", 0) or 0)
        if sale.empty:
            cases.append(_case(run_id, "refund_chargeback", "refund", r.get("event_id"), "sale", sid, None, amt, "orphan_event", "R4", 1.0, {"reason": "no linked sale"}, "high"))
        else:
            gross = float(sale.iloc[0].get("gross_amount", 0) or 0)
            if amt - gross > tol:
                cases.append(_case(run_id, "refund_chargeback", "refund", r.get("event_id"), "sale", sid, gross, amt, "amount_mismatch", "R4", 1.0, {"reason": "refund exceeds gross"}, "critical"))
            else:
                cases.append(_case(run_id, "refund_chargeback", "refund", r.get("event_id"), "sale", sid, gross, amt, "matched", "R4", 1.0, {"reason": "linked"}, "medium"))

    return pd.DataFrame(cases)
