from __future__ import annotations

from pathlib import Path

import pandas as pd


def export_reports(run_id: str, exports_dir: Path, tables: dict[str, pd.DataFrame]) -> dict[str, str]:
    run_dir = exports_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for name, df in tables.items():
        csv_path = run_dir / f"{name}.csv"
        df.to_csv(csv_path, index=False)
        paths[f"{name}_csv"] = str(csv_path)
    xlsx = run_dir / f"financial_report_{run_id}.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        for name, df in tables.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    paths["excel"] = str(xlsx)

    html = run_dir / f"summary_{run_id}.html"
    body = [f"<h1>Financial Intelligence Report - {run_id}</h1>"]
    for name, df in tables.items():
        body.append(f"<h2>{name}</h2>")
        body.append(df.head(200).to_html(index=False))
    html.write_text("\n".join(body), encoding="utf-8")
    paths["html"] = str(html)
    return paths
