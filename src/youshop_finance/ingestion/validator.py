from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pandas as pd

from youshop_finance.schemas import RAW_SCHEMAS


def _is_decimal(value: object) -> bool:
    try:
        Decimal(str(value))
        return True
    except (InvalidOperation, ValueError, TypeError):
        return False


def validate_raw(source: str, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    expected = RAW_SCHEMAS.get(source, [])
    missing_cols = [c for c in expected if c not in df.columns]
    if missing_cols:
        reject = df.copy()
        reject["validation_errors"] = f"missing_columns:{','.join(missing_cols)}"
        return df.iloc[0:0].copy(), reject

    valid_rows = []
    reject_rows = []
    for _, row in df.iterrows():
        errors: list[str] = []
        for col in expected:
            val = row.get(col)
            if pd.isna(val) or str(val).strip() == "":
                # allow optional refs in some sources
                optional = {
                    "gateway_payments": {"sale_id"},
                    "refunds_chargebacks": {"payment_id"},
                    "payouts": {"reference_id"},
                }
                if col in optional.get(source, set()):
                    continue
                errors.append(f"missing:{col}")
        for col in df.columns:
            if "amount" in col or "fee" in col or "net" in col or col == "commission_rate":
                if col in row and not pd.isna(row[col]) and str(row[col]).strip() != "":
                    if not _is_decimal(row[col]):
                        errors.append(f"invalid_decimal:{col}")
                    else:
                        try:
                            if Decimal(str(row[col])) < 0 and col != "diff_amount":
                                errors.append(f"negative:{col}")
                        except InvalidOperation:
                            pass
        if "sale_date" in df.columns:
            dt = pd.to_datetime(row.get("sale_date"), errors="coerce")
            if pd.isna(dt):
                errors.append("invalid_date:sale_date")
        if "payment_date" in df.columns and source == "gateway_payments":
            dt = pd.to_datetime(row.get("payment_date"), errors="coerce")
            if pd.isna(dt):
                errors.append("invalid_date:payment_date")
        if "event_date" in df.columns and source == "refunds_chargebacks":
            dt = pd.to_datetime(row.get("event_date"), errors="coerce")
            if pd.isna(dt):
                errors.append("invalid_date:event_date")
        if errors:
            rec = row.to_dict()
            rec["validation_errors"] = ";".join(errors)
            reject_rows.append(rec)
        else:
            valid_rows.append(row.to_dict())

    valid = pd.DataFrame(valid_rows, columns=list(df.columns))
    rejects = pd.DataFrame(reject_rows, columns=list(df.columns) + ["validation_errors"])
    return valid, rejects
