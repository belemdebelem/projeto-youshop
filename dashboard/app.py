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

STATUS_LABELS = {
    "matched": "Conciliado",
    "amount_mismatch": "Valor diferente",
    "missing_payment": "Pagamento ausente",
    "missing_sale": "Venda ausente",
    "duplicate_payment": "Pagamento duplicado",
    "commission_mismatch": "Comissão diferente",
    "missing_commission": "Comissão ausente",
    "duplicate_commission": "Comissão duplicada",
    "pending_payout": "Repasse pendente",
    "missing_payout": "Repasse ausente",
    "duplicate_payout": "Repasse duplicado",
    "ambiguous_match": "Correspondência incerta",
    "orphan_event": "Evento sem venda vinculada",
    "invalid_record": "Registro inválido",
    "technical_duplicate": "Duplicata técnica",
    "business_duplicate": "Duplicata de negócio",
}

CASE_TYPE_LABELS = {
    "sale_payment": "Venda x pagamento",
    "commission": "Comissão",
    "payout": "Repasse",
    "refund_chargeback": "Estorno/contestação",
}

RULE_LABELS = {
    "R1": "Regra 1 (venda e pagamento)",
    "R2": "Regra 2 (comissão)",
    "R3": "Regra 3 (repasse)",
    "R4": "Regra 4 (estorno/contestação)",
    "R5": "Regra 5",
    "R6": "Regra 6",
}

SEVERITY_LABELS = {
    "low": "Baixa",
    "medium": "Média",
    "high": "Alta",
    "critical": "Crítica",
}

ENTITY_TYPE_LABELS = {
    "sale": "venda",
    "gateway_payment": "pagamento",
    "commission": "comissão",
    "payout": "repasse",
    "refund": "estorno",
}

EVIDENCE_KEY_LABELS = {
    "reason": "Motivo",
    "diff": "Diferença",
    "expected_formula": "Cálculo esperado",
    "beneficiary_type": "Tipo de favorecido",
    "beneficiary_id": "Favorecido",
    "reference_id": "Referência",
}

EVIDENCE_VALUE_LABELS = {
    "no payment for sale": "não há pagamento para a venda",
    "multiple payments for same sale": "mais de um pagamento para a mesma venda",
    "payment without sale": "pagamento sem venda vinculada",
    "commission without sale": "comissão sem venda vinculada",
    "gross_amount*commission_rate": "valor bruto x alíquota da comissão",
    "extra payout for same reference": "repasse extra para a mesma referência",
    "no linked sale": "sem venda vinculada",
    "refund exceeds gross": "estorno maior que o valor bruto",
    "linked": "vinculado",
}

FEEDBACK_LABELS = {
    "pendente": "Ainda em análise",
    "confirmado": "Divergência confirmada",
    "falso_positivo": "Alarme falso",
    "causa_identificada": "Causa identificada",
}

EXPORT_LABELS = {
    "reconciliation_cases.csv": "Baixar todos os casos (CSV)",
    "divergences.csv": "Baixar divergências (CSV)",
    "anomaly_scores.csv": "Baixar índices de atipicidade (CSV)",
    "case_priority.csv": "Baixar fila priorizada (CSV)",
    "case_briefs.csv": "Baixar resumos (CSV)",
}


def rotulo(valor: object, mapa: dict[str, str]) -> str:
    texto = str(valor)
    return mapa.get(texto, texto.replace("_", " ").capitalize())


def brl(valor: object) -> str:
    if valor is None:
        return "—"
    try:
        if pd.isna(valor):
            return "—"
    except (TypeError, ValueError):
        pass
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    except (TypeError, ValueError):
        return str(valor)


def numero(valor: object) -> str:
    if valor is None:
        return "—"
    try:
        if pd.isna(valor):
            return "—"
    except (TypeError, ValueError):
        pass
    try:
        return f"{float(valor):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return str(valor)


def evidencias(raw: object) -> dict:
    try:
        dados = json.loads(raw or "{}")
        return dados if isinstance(dados, dict) else {}
    except (TypeError, ValueError):
        return {}


def linhas_evidencia(raw: object) -> list[str]:
    linhas = []
    for chave, valor in evidencias(raw).items():
        nome = rotulo(chave, EVIDENCE_KEY_LABELS)
        texto = EVIDENCE_VALUE_LABELS.get(str(valor), str(valor))
        linhas.append(f"- **{nome}:** {texto}")
    return linhas


def resumo_caso(caso: dict, nome_caso: str) -> str:
    situacao = rotulo(caso.get("reconciliation_status"), STATUS_LABELS)
    regra = rotulo(caso.get("match_rule"), RULE_LABELS)
    tipo_a = rotulo(caso.get("entity_a_type"), ENTITY_TYPE_LABELS)
    tipo_b = rotulo(caso.get("entity_b_type"), ENTITY_TYPE_LABELS)
    motivo = evidencias(caso.get("evidence_json")).get("reason")
    detalhe = f" Motivo: {EVIDENCE_VALUE_LABELS.get(str(motivo), str(motivo))}." if motivo else ""
    return (
        f"**Resumo:** {nome_caso} — {situacao} ({regra}). "
        f"Evidências: {tipo_a} {caso.get('entity_a_id')} x {tipo_b} {caso.get('entity_b_id')}; "
        f"esperado {brl(caso.get('expected_amount'))}; "
        f"encontrado {brl(caso.get('actual_amount'))}; "
        f"diferença {brl(caso.get('diff_amount'))}.{detalhe} "
        "Sugestão: conferir a origem dos registros e registrar a decisão."
    )


def opcao_execucao(linha: pd.Series) -> str:
    data = pd.to_datetime(linha.get("started_at"), utc=True, errors="coerce")
    quando = data.strftime("%d/%m %H:%M") if pd.notna(data) else "sem data"
    return f"{quando} · {str(linha.get('run_id', ''))[-8:]}"


def rotulo_export(nome: str) -> str:
    if nome.startswith("financial_report_"):
        return "Baixar relatório financeiro (Excel)"
    if nome.startswith("summary_"):
        return "Baixar resumo visual (HTML)"
    return EXPORT_LABELS.get(nome, f"Baixar {nome}")


st.set_page_config(page_title="Radar Financeiro Inteligente", layout="wide")
st.markdown(
    """
    <style>
      h1, h2, h3 { color: #0D284D; }
      .bloco-dica { font-size: 0.88rem; color: #334155; }
      .id-tecnico { font-size: 0.72rem; color: #64748B; word-break: break-all; }
      div[data-testid="stMetricLabel"] { font-size: 0.85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Radar Financeiro Inteligente")
st.caption(
    "Conciliação, divergências e prioridade de análise em um só lugar. "
    "Ambiente de demonstração com dados sintéticos."
)
st.markdown(
    '<p class="bloco-dica"><strong>Como usar:</strong> '
    "1) escolha a execução · 2) leia os indicadores · "
    "3) selecione um caso · 4) baixe um relatório.</p>",
    unsafe_allow_html=True,
)

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
    runs = load_table(
        "SELECT run_id, status, started_at, summary_json "
        "FROM audit_runs ORDER BY started_at DESC"
    )
    if runs.empty:
        with st.spinner("Gerando dados e processando conciliação..."):
            _run_cmd([sys.executable, "scripts/generate_synthetic_data.py"])
            run_id = run_pipeline()
        st.cache_data.clear()
        return run_id
    return str(runs.iloc[0]["run_id"])


col_a, _ = st.columns([1, 1])
with col_a:
    if st.button("Gerar nova análise", type="primary"):
        _run_cmd([sys.executable, "scripts/generate_synthetic_data.py"])
        new_run = run_pipeline()
        st.cache_data.clear()
        st.success(f"Nova análise concluída: {new_run}")

latest_run = ensure_data()
runs = load_table(
    "SELECT run_id, status, started_at, summary_json "
    "FROM audit_runs ORDER BY started_at DESC"
)
opcoes_execucao = [opcao_execucao(row) for _, row in runs.iterrows()]
execucao_por_opcao = dict(zip(opcoes_execucao, runs["run_id"].astype(str), strict=True))
execucao_selecionada = st.selectbox(
    "Execução",
    opcoes_execucao,
    index=0 if opcoes_execucao else None,
    help="Troque a execução para comparar outra rodada da análise.",
)
run_id = str(execucao_por_opcao.get(execucao_selecionada, latest_run))

recon = load_table("SELECT * FROM gold_reconciliation_cases WHERE run_id = ?", [run_id])
div = load_table("SELECT * FROM gold_divergences WHERE run_id = ?", [run_id])
anom = load_table("SELECT * FROM gold_anomaly_scores WHERE run_id = ?", [run_id])
prio = load_table(
    """
    SELECT p.*, c.case_type, c.reconciliation_status, c.match_rule,
           c.entity_a_type, c.entity_a_id, c.entity_b_type, c.entity_b_id,
           c.expected_amount, c.actual_amount, c.diff_amount, c.severity, c.evidence_json
    FROM gold_case_priority p
    JOIN gold_reconciliation_cases c USING(case_id, run_id)
    WHERE p.run_id = ?
    ORDER BY p.priority_score DESC
    """,
    [run_id],
)

total_cases = len(recon)
matched = int((recon["reconciliation_status"] == "matched").sum()) if not recon.empty else 0
div_count = total_cases - matched
diferencas = pd.to_numeric(div.get("diff_amount", pd.Series(dtype=float)), errors="coerce")
div_value = float(diferencas.abs().fillna(0).sum()) if not div.empty else 0.0
anom_flag = int(anom["is_anomaly"].sum()) if not anom.empty else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric(
    "Itens conciliados",
    f"{matched}/{total_cases}",
    help="Registros de vendas, pagamentos, comissões e repasses que conferem entre as fontes.",
)
k2.metric(
    "Conciliação automática",
    f"{(matched / total_cases * 100):.1f}%" if total_cases else "0%",
    help="Percentual de itens que não precisaram de investigação.",
)
k3.metric(
    "Itens que não batem",
    div_count,
    help="Casos em que os valores ou registros das fontes não conferem.",
)
k4.metric(
    "Valor em divergência",
    brl(div_value),
    help="Soma absoluta das diferenças encontradas.",
)
k5.metric(
    "Casos atípicos sinalizados",
    anom_flag,
    help="Operações fora do padrão habitual que entraram para revisão.",
)
st.markdown(
    '<p class="bloco-dica">Os indicadores resumem esta execução. '
    "A fila abaixo mostra por onde começar.</p>",
    unsafe_allow_html=True,
)

st.divider()
left, right = st.columns([1.35, 1])
with left:
    st.subheader("Por onde começar")
    if prio.empty:
        st.info("Nenhuma divergência para investigar nesta execução.")
    else:
        ids_caso = prio["case_id"].astype(str).tolist()
        nomes_caso = [f"Caso {i:02d}" for i in range(1, len(ids_caso) + 1)]
        nome_por_id = dict(zip(ids_caso, nomes_caso, strict=True))
        id_por_nome = dict(zip(nomes_caso, ids_caso, strict=True))
        tabela = pd.DataFrame(
            {
                "Caso": nomes_caso,
                "Tipo": [rotulo(v, CASE_TYPE_LABELS) for v in prio["case_type"]],
                "Situação": [rotulo(v, STATUS_LABELS) for v in prio["reconciliation_status"]],
                "Regra": [rotulo(v, RULE_LABELS) for v in prio["match_rule"]],
                "Gravidade": [rotulo(v, SEVERITY_LABELS) for v in prio["severity"]],
                "Impacto financeiro": [numero(v) for v in prio["financial_severity"]],
                "Atipicidade": [numero(v) for v in prio["anomaly_score"]],
                "Urgência": [numero(v) for v in prio["urgency_score"]],
                "Prioridade": [numero(v) for v in prio["priority_score"]],
                "Registro A": [
                    f"{rotulo(tipo, ENTITY_TYPE_LABELS)} · {identificador}"
                    for tipo, identificador in zip(
                        prio["entity_a_type"], prio["entity_a_id"], strict=True
                    )
                ],
                "Registro B": [
                    f"{rotulo(tipo, ENTITY_TYPE_LABELS)} · {identificador}"
                    for tipo, identificador in zip(
                        prio["entity_b_type"], prio["entity_b_id"], strict=True
                    )
                ],
                "Diferença (R$)": [brl(v) for v in prio["diff_amount"]],
            }
        )
        st.dataframe(tabela, use_container_width=True, hide_index=True)
        st.markdown(
            '<p class="bloco-dica">Comece pelo primeiro da lista: ele tem a maior prioridade. '
            "Escolha um caso na lista ao lado para ver os detalhes.</p>",
            unsafe_allow_html=True,
        )
with right:
    st.subheader("Onde estão os problemas")
    if div.empty:
        st.info("Nenhuma divergência nesta execução — todos os itens conciliaram.")
    else:
        contagem = div["reconciliation_status"].value_counts()
        grafico = pd.DataFrame(
            {"Casos": contagem.to_numpy()},
            index=[rotulo(status, STATUS_LABELS) for status in contagem.index],
        )
        st.bar_chart(grafico, horizontal=True, sort=False, use_container_width=True)
        st.markdown(
            '<p class="bloco-dica">Este gráfico mostra apenas os itens que não conciliaram. '
            "Os itens conciliados aparecem no indicador acima.</p>",
            unsafe_allow_html=True,
        )

st.subheader("Detalhes do caso selecionado")
if prio.empty:
    st.write("Nenhum caso disponível nesta execução.")
else:
    opcoes_caso = [
        f"{nome_por_id[cid]} · {rotulo(status, STATUS_LABELS)} · {brl(diferenca)}"
        for cid, status, diferenca in zip(
            ids_caso, prio["reconciliation_status"], prio["diff_amount"], strict=True
        )
    ]
    opcao_caso = st.selectbox(
        "Escolha outro caso para ver os detalhes",
        opcoes_caso,
        help="A ordem segue a prioridade de investigação.",
    )
    nome_caso = opcao_caso.split(" · ", 1)[0]
    case_id = str(id_por_nome[nome_caso])
    caso = prio[prio["case_id"].astype(str) == case_id].iloc[0].to_dict()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{nome_caso} — {rotulo(caso.get('reconciliation_status'), STATUS_LABELS)}**")
        st.write(f"**Tipo:** {rotulo(caso.get('case_type'), CASE_TYPE_LABELS)}")
        st.write(f"**Regra aplicada:** {rotulo(caso.get('match_rule'), RULE_LABELS)}")
        st.write(f"**Gravidade:** {rotulo(caso.get('severity'), SEVERITY_LABELS)}")
        st.write(f"**Valor esperado:** {brl(caso.get('expected_amount'))}")
        st.write(f"**Valor encontrado:** {brl(caso.get('actual_amount'))}")
        st.write(f"**Diferença:** {brl(caso.get('diff_amount'))}")
        st.markdown(
            f'<p class="id-tecnico">ID técnico: {case_id}</p>',
            unsafe_allow_html=True,
        )
        st.markdown("**Por que este caso apareceu**")
        linhas = linhas_evidencia(caso.get("evidence_json"))
        if linhas:
            st.markdown("\n".join(linhas))
        else:
            st.write("Sem evidências adicionais.")
    with c2:
        st.markdown("**Resumo para investigação**")
        st.markdown(
            '<p class="bloco-dica">Leitura automática das evidências. '
            "A decisão final é humana.</p>",
            unsafe_allow_html=True,
        )
        st.write(resumo_caso(caso, nome_caso))

        st.markdown("**Registrar decisão**")
        st.markdown(
            '<p class="bloco-dica">Registre o que foi concluído para acompanhar depois.</p>',
            unsafe_allow_html=True,
        )
        with st.form("feedback_form"):
            opcoes_feedback = list(FEEDBACK_LABELS.values())
            escolha = st.selectbox("Resultado da revisão", opcoes_feedback)
            analyst_label = next(
                chave for chave, texto in FEEDBACK_LABELS.items() if texto == escolha
            )
            cause = st.text_input("Causa encontrada")
            notes = st.text_area("Observações (opcional)")
            submitted = st.form_submit_button("Salvar decisão")
            if submitted:
                fb = pd.DataFrame(
                    [
                        {
                            "feedback_id": f"{run_id}:{case_id}:{pd.Timestamp.utcnow().value}",
                            "case_id": case_id,
                            "run_id": run_id,
                            "analyst_label": analyst_label,
                            "cause_code": cause,
                            "notes": notes,
                            "decided_at": pd.Timestamp.utcnow().isoformat(),
                            "decided_by": "analyst_local",
                        }
                    ]
                )
                repo.write_df("gold_analyst_feedback", fb, mode="append")
                st.success("Decisão registrada.")

st.subheader("Relatórios para baixar")
export_dir = settings.data_exports_dir / run_id
if export_dir.exists():
    st.markdown(
        '<p class="bloco-dica">Clique em um botão para baixar o arquivo.</p>',
        unsafe_allow_html=True,
    )
    for f in sorted(export_dir.glob("*")):
        with f.open("rb") as fh:
            st.download_button(rotulo_export(f.name), fh, file_name=f.name)
else:
    st.info("Nenhum relatório disponível para esta execução.")
