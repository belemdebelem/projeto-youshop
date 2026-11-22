from __future__ import annotations

from dataclasses import dataclass

RAW_SCHEMAS: dict[str, list[str]] = {
    "sales": [
        "sale_id",
        "order_id",
        "producer_id",
        "creator_id",
        "gross_amount",
        "platform_fee",
        "net_amount",
        "sale_date",
        "status",
    ],
    "gateway_payments": [
        "payment_id",
        "order_id",
        "sale_id",
        "amount_captured",
        "payment_date",
        "status",
        "gateway_ref",
    ],
    "commissions": [
        "commission_id",
        "sale_id",
        "creator_id",
        "commission_rate",
        "expected_commission",
        "status",
    ],
    "producer_receivables": [
        "receivable_id",
        "sale_id",
        "producer_id",
        "amount_due",
        "due_date",
        "status",
    ],
    "payouts": [
        "payout_id",
        "beneficiary_type",
        "beneficiary_id",
        "reference_id",
        "amount_paid",
        "payout_date",
        "status",
    ],
    "refunds_chargebacks": [
        "event_id",
        "sale_id",
        "payment_id",
        "amount",
        "event_date",
        "event_type",
        "reason",
    ],
}


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: list[str]
