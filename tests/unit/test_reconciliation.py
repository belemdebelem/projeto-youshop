from pathlib import Path

import pandas as pd

from youshop_finance.reconciliation.engine import ReconConfig, reconcile


def test_reconciliation_detects_mismatch_and_missing():
    silver = {
        "sales": pd.DataFrame([{"sale_id": "S1", "order_id": "O1", "producer_id": "P1", "creator_id": "C1", "gross_amount": 100.0, "platform_fee": 8.0, "net_amount": 92.0, "sale_date": "2026-01-01", "status": "approved"}]),
        "gateway_payments": pd.DataFrame([{"payment_id": "PAY1", "order_id": "O1", "sale_id": "S1", "amount_captured": 90.0, "payment_date": "2026-01-01", "status": "captured", "gateway_ref": "GW1"}]),
        "commissions": pd.DataFrame([{"commission_id": "COM1", "sale_id": "S1", "creator_id": "C1", "commission_rate": 0.1, "expected_commission": 10.0, "status": "calculated"}]),
        "payouts": pd.DataFrame([]),
        "refunds_chargebacks": pd.DataFrame([]),
    }
    df = reconcile("run1", silver, ReconConfig())
    statuses = set(df["reconciliation_status"])
    assert "amount_mismatch" in statuses
    assert "missing_payout" in statuses
