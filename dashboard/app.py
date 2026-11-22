from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (str(SRC), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from youshop_finance.config import get_settings
from youshop_finance.pipeline.run import run_pipeline
from youshop_finance.storage.duckdb_repo import DuckDBRepo

st.set_page_config(page_title="YouShop Financial Intelligence", layout="wide")
st.title("Financial Intelligence & Reconciliation Platform")
st.caption("MVP Finanças e Controladoria — conciliação determinística + priorização de exceções + briefing assistivo")

settings = get_settings()
repo = DuckDBRepo(settings.duckdb_path)


@st.cache_data(ttl=30)
def load_table(sql: str, params: list | None = None) -> pd.DataFrame:
    try:
        return repo.query_df(sql, params or [])
    except Exception:
        return pd.DataFrame()


def _run_cmd(args: list[str]) -> None:
    env = os.environ.copy()
    py_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(SRC) if not py_path else f"{SRC}{os.pathsep}{py_path}"
    subprocess.check_call(args, cwd=settings.project_root, env=env)


def ensure_data() -> str:
    repo.init_schema()
    runs = load_table("SELECT run_id, status, started_at, summary_json FROM audit_runs ORDER BY started_at DESC")
    if runs.empty:
        with st.spinner("Gerando dados sintéticos e executando pipeline..."):
            _run_cmd([sys.executable, "scripts/generate_synthetic_data.py"])
            run_id = run_pipeline()
        st.cache_data.clear()
        return run_id
    return str(runs.iloc[0]["run_id"])


col_a, col_b = st.columns([1, 1])
with col_a:
    if st.button("Gerar dados e executar pipeline", type="primary"):
        _run_cmd([sys.executable, "scripts/generate_synthetic_data.py"])
        new_run = run_pipeline()
        st.cache_data.clear()
        st.success(f"Pipeline executado: {new_run}")

latest_run = ensure_data()
runs = load_table("SELECT run_id, status, started_at, summary_json FROM audit_runs ORDER BY started_at DESC")
run_id = st.selectbox("Execução (run_id)", runs["run_id"].tolist(), index=0 if not runs.empty else None)

recon = load_table("SELECT * FROM gold_reconciliation_cases WHERE run_id = ?", [run_id])
div = load_table("SELECT * FROM gold_divergences WHERE run_id = ?", [run_id])
anom = load_table("SELECT * FROM gold_anomaly_scores WHERE run_id = ?", [run_id])
prio = load_table(
    """
    SELECT p.*, c.case_type, c.reconciliation_status, c.match_rule, c.entity_a_type, c.entity_a_id,
           c.entity_b_type, c.entity_b_id, c.expected_amount, c.actual_amount, c.diff_amount, c.severity, c.evidence_json
    FROM gold_case_priority p
    JOIN gold_reconciliation_cases c USING(case_id, run_id)
    WHERE p.run_id = ?
    ORDER BY p.priority_score DESC
    """,
    [run_id],
)
briefs = load_table("SELECT * FROM gold_case_briefs WHERE run_id = ?", [run_id])

# KPIs
k1, k2, k3, k4, k5 = st.columns(5)
total_cases = len(recon)
matched = int((recon["reconciliation_status"] == "matched").sum()) if not recon.empty else 0
div_count = total_cases - matched
div_value = float(pd.to_numeric(div.get("diff_amount", pd.Series(dtype=float)), errors="coerce").abs().fillna(0).sum()) if not div.empty else 0.0
anom_flag = int(anom["is_anomaly"].sum()) if not anom.empty else 0
k1.metric("Casos conciliados", f"{matched}/{total_cases}")
k2.metric("% Conciliação automática", f"{(matched/total_cases*100):.1f}%" if total_cases else "0%")
k3.metric("Divergências", div_count)
k4.metric("Valor absoluto divergências", f"R$ {div_value:,.2f}")
k5.metric("Anomalias sinalizadas", anom_flag)

st.divider()
left, right = st.columns([1.2, 1])
with left:
    st.subheader("Fila de investigação priorizada")
    if prio.empty:
        st.info("Sem divergências para priorização.")
    else:
        show = prio[["case_id","case_type","reconciliation_status","match_rule","severity","financial_severity","anomaly_score","urgency_score","priority_score","entity_a_id","entity_b_id","diff_amount"]]
        st.dataframe(show, use_container_width=True, hide_index=True)
with right:
    st.subheader("Distribuição por status")
    if recon.empty:
        st.info("Sem dados.")
    else:
        st.bar_chart(recon["reconciliation_status"].value_counts())

st.subheader("Drill-down do caso")
if prio.empty:
    st.write("Nenhum caso divergente.")
else:
    case_id = st.selectbox("Caso", prio["case_id"].tolist())
    case = prio[prio["case_id"] == case_id].iloc[0].to_dict()
    brief = briefs[briefs["case_id"] == case_id]
    c1, c2 = st.columns(2)
    with c1:
        st.json({k: case.get(k) for k in ["case_id","case_type","reconciliation_status","match_rule","severity","expected_amount","actual_amount","diff_amount","priority_score","anomaly_score"]})
        try:
            st.write("Evidência:", json.loads(case.get("evidence_json") or "{}"))
        except Exception:
            st.write(case.get("evidence_json"))
    with c2:
        st.markdown("**Briefing investigativo (assistivo)**")
        if brief.empty:
            st.warning("Briefing não encontrado.")
        else:
            st.write(brief.iloc[0]["brief_text"])
        st.markdown("**Feedback do analista**")
        with st.form("feedback_form"):
            label = st.selectbox("Classificação", ["confirmado", "falso_positivo", "causa_identificada", "pendente"])
            cause = st.text_input("Causa")
            notes = st.text_area("Observações")
            submitted = st.form_submit_button("Salvar feedback")
            if submitted:
                fb = pd.DataFrame([{
                    "feedback_id": f"{run_id}:{case_id}:{pd.Timestamp.utcnow().value}",
                    "case_id": case_id, "run_id": run_id, "analyst_label": label,
                    "cause_code": cause, "notes": notes, "decided_at": pd.Timestamp.utcnow().isoformat(), "decided_by": "analyst_local",
                }])
                repo.write_df("gold_analyst_feedback", fb, mode="append")
                st.success("Feedback salvo.")

st.subheader("Exports")
export_dir = settings.data_exports_dir / run_id
if export_dir.exists():
    for f in sorted(export_dir.glob("*")):
        with f.open("rb") as fh:
            st.download_button(f"Baixar {f.name}", fh, file_name=f.name)
else:
    st.info("Exports não encontrados para esta execução.")
