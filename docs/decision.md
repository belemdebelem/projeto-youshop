# Decisão Arquitetural — Financial Intelligence & Reconciliation Platform

## Contexto
Projeto de inovação para o processo seletivo de estágio **YouShop 2027**, com foco exclusivo em **Financeiro e Controladoria**. O objetivo é entregar um **protótipo funcional local** que automatize conciliação, priorize exceções com IA/ML e apoie investigação analítica, usando dados sintéticos.

## Problema priorizado
- Conciliação manual entre vendas, pagamentos/gateway, comissões, recebíveis de produtores, repasses/saques e estornos/chargebacks.
- Divergências, duplicidades, registros ausentes e inconsistências entre fontes.
- Consolidação lenta de relatórios/indicadores e baixa rastreabilidade das decisões.

## Usuários e áreas impactadas
- **Financeiro:** conferência de pagamentos, comissões, repasses/saques e ajustes; investigação de exceções.
- **Controladoria:** consolidação de dados, indicadores, auditoria e suporte à tomada de decisão.

## Alternativas consideradas e descartadas
| Alternativa | Motivo do descarte |
|---|---|
| BI estático + automação de planilhas | Não atende ao critério de IA central no desafio; baixa priorização inteligente de exceções. |
| Apenas regras determinísticas + template | Seguro, mas fraco como diferencial de IA no critério do desafio. |
| LLM obrigatória no MVP | Risco de dependência, custo/variabilidade, fragilidade de demo offline e risco de explicações não grounded. |
| Infra cloud/serviços gerenciados no MVP | Complexidade e custo desnecessários para protótipo local. |
| Polars como padrão | Ganho improvável no volume sintético; Pandas mais simples para o escopo. |

## Arquitetura final (resumo)
Pipeline local com Medallion lógico (Bronze/Silver/Gold) em DuckDB, orquestrado em Python:

```text
Fontes CSV/Excel -> Ingestão/Validação (Pandas)
  -> Bronze (imutável por run_id, manifesto)
  -> Silver (padronizado, deduplicado, quarentena)
  -> Conciliação Determinística (R1-R6)
  -> Inteligência de Exceções (baseline MAD/IQR + Isolation Forest)
  -> Priorização Transparente (financeiro + atipicidade + urgência)
  -> Gold (DuckDB) + Auditoria
  -> Streamlit (fila, drill-down, briefing, feedback) + Exports (CSV/Excel/HTML)
```

## Decisões-chave
- **Conciliação é determinística e fonte de verdade financeira** (`reconciliation_status` não é alterado por ML/GenAI).
- **IA principal:** ML de anomalia/priorização + briefing grounded plugável com fallback determinístico.
- **Diferencial posicionamento:** “Inteligência e Investigação de Exceções Financeiras”, não apenas “detector de anomalias”.
- **GenAI (Decisão 1):** **C — nenhuma LLM obrigatória no MVP**. `TemplateProvider` obrigatório; `LLMProvider` interface opcional futura, fora do caminho crítico.
- **Stack:** Python, Pandas, DuckDB, Streamlit, scikit-learn, Pytest.
- **Infra:** local-first; evolução cloud apenas documentada.

## Escopo do MVP
Incluído:
- Geração de dados sintéticos com ground truth.
- Ingestão, validação, Bronze/Silver/Gold em DuckDB.
- Conciliação determinística R1-R6 com evidência.
- Baseline MAD/IQR + Isolation Forest comparado, com métricas e reason codes.
- Priorização transparente (`priority_score`).
- `TemplateProvider` grounded e registro de feedback analista.
- Dashboard Streamlit + exports CSV/Excel/HTML + auditoria por `run_id`.

Excluído:
- LLM obrigatória/chatbot, decisões autônomas, integrações reais, cloud no MVP, áreas fora de Finanças/Controladoria, auto-treinamento em runtime.

## KPIs do MVP
- Tempo de processamento por execução.
- Percentual de conciliação automatizada.
- Quantidade e valor total de divergências.
- `Precision@K`, precision/recall/F1 na detecção de anomalias (com ground truth).
- Taxa de falsos positivos da fila priorizada.
- Tempo estimado de consolidação manual vs automatizado (comparação simulada).

## Riscos e mitigação
- **Falsos positivos em anomalias:** baseline MAD/IQR + comparação com IF + ground truth + razão explícita.
- **Ambiguidade em match:** proibir auto-match ambíguo (`ambiguous_match` para revisão humana).
- **Explicação não grounded:** briefing limitado a evidências do caso/Gold.
- **Não reprodutibilidade:** versionar regras/modelo/config e registrar em `audit_runs/audit_model_runs`.

## Critério de conclusão
Protótipo local executável ponta a ponta com dados sintéticos, conciliação rastreável, priorização explicável, briefing grounded, feedback persistido, exports e documentação suficiente para demonstração.