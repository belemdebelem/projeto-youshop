from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from youshop_finance.config import get_settings


def money(x: float) -> float:
    return float(np.round(x, 2))


def main(seed: int = 42, n_sales: int = 240) -> None:
    rng = np.random.default_rng(seed)
    settings = get_settings()
    out = settings.data_raw_dir
    out.mkdir(parents=True, exist_ok=True)

    start = date(2026, 1, 1)
    producers = [f"PROD_{i:03d}" for i in range(1, 9)]
    creators = [f"CRT_{i:03d}" for i in range(1, 13)]

    sales = []
    gateway = []
    commissions = []
    receivables = []
    payouts = []
    refunds = []
    truth = []

    for i in range(1, n_sales + 1):
        sale_id = f"SAL_{i:05d}"
        order_id = f"ORD_{i:05d}"
        producer_id = rng.choice(producers)
        creator_id = rng.choice(creators)
        sale_date = start + timedelta(days=int(rng.integers(0, 120)))
        gross = money(float(rng.choice([49.9, 79.9, 99.9, 149.9, 199.9, 299.9, 499.9])))
        fee = money(gross * 0.08)
        net = money(gross - fee)
        rate = float(rng.choice([0.05, 0.08, 0.10, 0.12]))
        comm = money(gross * rate)
        status = "approved"

        sales.append(
            {
                "sale_id": sale_id,
                "order_id": order_id,
                "producer_id": producer_id,
                "creator_id": creator_id,
                "gross_amount": gross,
                "platform_fee": fee,
                "net_amount": net,
                "sale_date": sale_date.isoformat(),
                "status": status,
            }
        )
        gateway.append(
            {
                "payment_id": f"PAY_{i:05d}",
                "order_id": order_id,
                "sale_id": sale_id,
                "amount_captured": gross,
                "payment_date": (sale_date + timedelta(days=int(rng.integers(0, 2)))).isoformat(),
                "status": "captured",
                "gateway_ref": f"GW-{i:06d}",
            }
        )
        commissions.append(
            {
                "commission_id": f"COM_{i:05d}",
                "sale_id": sale_id,
                "creator_id": creator_id,
                "commission_rate": rate,
                "expected_commission": comm,
                "status": "calculated",
            }
        )
        receivables.append(
            {
                "receivable_id": f"REC_{i:05d}",
                "sale_id": sale_id,
                "producer_id": producer_id,
                "amount_due": net,
                "due_date": (sale_date + timedelta(days=7)).isoformat(),
                "status": "pending",
            }
        )
        payouts.append(
            {
                "payout_id": f"POC_{i:05d}",
                "beneficiary_type": "creator",
                "beneficiary_id": creator_id,
                "reference_id": sale_id,
                "amount_paid": comm,
                "payout_date": (sale_date + timedelta(days=int(rng.integers(7, 15)))).isoformat(),
                "status": "paid",
            }
        )
        payouts.append(
            {
                "payout_id": f"POP_{i:05d}",
                "beneficiary_type": "producer",
                "beneficiary_id": producer_id,
                "reference_id": sale_id,
                "amount_paid": net,
                "payout_date": (sale_date + timedelta(days=int(rng.integers(7, 15)))).isoformat(),
                "status": "paid",
            }
        )
        truth.append({"entity_type": "sale", "entity_id": sale_id, "scenario": "normal", "expected_issue": None})

    # Inject scenarios
    # 1) amount mismatch gateway
    idx = 5
    gateway[idx]["amount_captured"] = money(gateway[idx]["amount_captured"] - 20.0)
    truth.append({"entity_type": "payment", "entity_id": gateway[idx]["payment_id"], "scenario": "amount_mismatch", "expected_issue": "R1_amount_mismatch"})

    # 2) missing payment
    missing_pay = gateway.pop(10)
    truth.append({"entity_type": "sale", "entity_id": missing_pay["sale_id"], "scenario": "missing_payment", "expected_issue": "R1_missing_payment"})

    # 3) duplicate payment
    dup = gateway[20].copy()
    dup["payment_id"] = "PAY_DUP_0001"
    dup["gateway_ref"] = "GW-DUP-0001"
    gateway.append(dup)
    truth.append({"entity_type": "payment", "entity_id": dup["payment_id"], "scenario": "duplicate_payment", "expected_issue": "R1_duplicate_payment"})

    # 4) commission mismatch
    commissions[15]["expected_commission"] = money(commissions[15]["expected_commission"] - 15.0)
    truth.append({"entity_type": "commission", "entity_id": commissions[15]["commission_id"], "scenario": "commission_mismatch", "expected_issue": "R2_commission_mismatch"})

    # 5) missing payout
    removed_payout = payouts.pop(30)
    truth.append({"entity_type": "payout_expected", "entity_id": removed_payout["reference_id"], "scenario": "missing_payout", "expected_issue": "R3_missing_payout"})

    # 6) orphan refund/chargeback
    refunds.append(
        {
            "event_id": "EVT_ORPH_0001",
            "sale_id": "SAL_99999",
            "payment_id": "PAY_99999",
            "amount": 99.9,
            "event_date": (start + timedelta(days=40)).isoformat(),
            "event_type": "chargeback",
            "reason": "orphan_test",
        }
    )
    truth.append({"entity_type": "refund", "entity_id": "EVT_ORPH_0001", "scenario": "orphan_event", "expected_issue": "R4_orphan_event"})

    # 7) statistical anomaly - high amount sale correctly reconciled
    anomaly_sale_id = "SAL_ANOM_0001"
    anomaly_order = "ORD_ANOM_0001"
    anomaly_date = (start + timedelta(days=60)).isoformat()
    gross = 3999.9
    fee = money(gross * 0.08)
    net = money(gross - fee)
    rate = 0.12
    comm = money(gross * rate)
    sales.append({"sale_id": anomaly_sale_id, "order_id": anomaly_order, "producer_id": "PROD_001", "creator_id": "CRT_001", "gross_amount": gross, "platform_fee": fee, "net_amount": net, "sale_date": anomaly_date, "status": "approved"})
    gateway.append({"payment_id": "PAY_ANOM_0001", "order_id": anomaly_order, "sale_id": anomaly_sale_id, "amount_captured": gross, "payment_date": anomaly_date, "status": "captured", "gateway_ref": "GW-ANOM-0001"})
    commissions.append({"commission_id": "COM_ANOM_0001", "sale_id": anomaly_sale_id, "creator_id": "CRT_001", "commission_rate": rate, "expected_commission": comm, "status": "calculated"})
    receivables.append({"receivable_id": "REC_ANOM_0001", "sale_id": anomaly_sale_id, "producer_id": "PROD_001", "amount_due": net, "due_date": anomaly_date, "status": "pending"})
    payouts.append({"payout_id": "POC_ANOM_0001", "beneficiary_type": "creator", "beneficiary_id": "CRT_001", "reference_id": anomaly_sale_id, "amount_paid": comm, "payout_date": anomaly_date, "status": "paid"})
    payouts.append({"payout_id": "POP_ANOM_0001", "beneficiary_type": "producer", "beneficiary_id": "PROD_001", "reference_id": anomaly_sale_id, "amount_paid": net, "payout_date": anomaly_date, "status": "paid"})
    truth.append({"entity_type": "sale", "entity_id": anomaly_sale_id, "scenario": "statistical_anomaly", "expected_issue": "ANOM_high_amount"})

    # Invalid record
    sales.append({"sale_id": "SAL_BAD_0001", "order_id": "", "producer_id": "PROD_001", "creator_id": "CRT_001", "gross_amount": -10, "platform_fee": 0, "net_amount": -10, "sale_date": "2026-99-99", "status": "approved"})
    truth.append({"entity_type": "sale", "entity_id": "SAL_BAD_0001", "scenario": "invalid_record", "expected_issue": "R5_invalid"})

    pd.DataFrame(sales).to_csv(out / "sales.csv", index=False)
    pd.DataFrame(gateway).to_csv(out / "gateway_payments.csv", index=False)
    pd.DataFrame(commissions).to_csv(out / "commissions.csv", index=False)
    pd.DataFrame(receivables).to_csv(out / "producer_receivables.csv", index=False)
    pd.DataFrame(payouts).to_csv(out / "payouts.csv", index=False)
    pd.DataFrame(refunds).to_csv(out / "refunds_chargebacks.csv", index=False)
    (out / "ground_truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated synthetic data in {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--n-sales", type=int, default=240)
    args = parser.parse_args()
    s = get_settings()
    main(seed=args.seed if args.seed is not None else s.default_seed, n_sales=args.n_sales)
