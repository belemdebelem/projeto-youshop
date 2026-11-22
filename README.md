# Financial Intelligence & Reconciliation Platform (MVP)

Protótipo funcional para o **Desafio de Inovação – Programa de Estágio YouShop 2027**, focado exclusivamente em **Financeiro e Controladoria**.

A solução automatiza ingestão, validação, conciliação determinística, priorização de exceções com ML explicável e apoio investigativo assistivo, usando dados sintéticos.

## O que o MVP entrega

- **Pipeline Medallion local** (Bronze/Silver/Gold) com DuckDB.
- **Conciliação determinística R1-R6** (fonte de verdade financeira).
- **Inteligência de exceções**: baseline robusto (MAD/IQR) + Isolation Forest para `anomaly_score`.
- **Priorização transparente**: `priority_score = financeiro + atipicidade + urgência` (+ override crítico).
- **Briefing investigativo grounded** por `TemplateProvider` (assistivo, sem decisão financeira).
- **Dashboard Streamlit** com KPIs, fila priorizada, drill-down, feedback do analista e exports.
- **Auditoria por `run_id`**: manifesto, contagens, erros, modelo/config/rules versionadas.

## Arquitetura

```text
Raw CSV/Excel -> Ingestão/Validação -> Bronze (imutável)
  -> Silver (DuckDB) -> Conciliação Determinística R1-R6
  -> ML Anomalia/Prioridade -> Gold + Auditoria
  -> Streamlit Dashboard + Exports CSV/Excel/HTML
```

Documentação detalhada em `docs/`:
- `docs/decision.md`
- `docs/architecture.md`
- `docs/data-model.md`
- `docs/reconciliation-rules.md`
- `docs/anomaly-strategy.md`
- `docs/mvp-scope.md`
- `docs/assumptions.md`
- `docs/implementation-plan.md`

## Execução local

### 1) Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Gerar dados sintéticos
```bash
PYTHONPATH=src python scripts/generate_synthetic_data.py
```

### 3) Executar pipeline
```bash
PYTHONPATH=src python scripts/run_pipeline.py
```

### 4) Abrir dashboard
```bash
PYTHONPATH=src streamlit run dashboard/app.py
```

## Deploy como protótipo (link)

### Streamlit Community Cloud (recomendado)
1. Suba este repositório no GitHub.
2. Em https://share.streamlit.io, crie um app apontando para `dashboard/app.py`.
3. Defina Python 3.11+ e instale via `requirements.txt`.
4. O app gera dados e executa o pipeline automaticamente se não houver execução prévia.

### Observações para avaliadores
- Dados são **sintéticos** e não representam dados reais da YouShop.
- A IA/ML **não toma decisões financeiras**; conciliação é determinística e auditável.
- LLM generativa **não é obrigatória** no MVP; há interface/fallback por template.

## Testes

```bash
PYTHONPATH=src pytest
```

## Limites do MVP

- Sem integração com sistemas reais YouShop.
- Sem cloud/infra distribuída no MVP.
- Sem auto-treinamento com feedback humano em runtime.
- Sem ações financeiras autônomas/irreversíveis.