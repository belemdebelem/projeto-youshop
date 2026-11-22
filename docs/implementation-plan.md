# Plano de Implementação Incremental

## Fase 1 — Decisão e desenho (concluída na documentação)
**Entregas:** `decision.md`, `data-model.md`, `reconciliation-rules.md`, `anomaly-strategy.md`, `assumptions.md`, `mvp-scope.md`.  
**Aceite:** escopo fechado, regras R1-R6 definidas, sinais separados (`reconciliation_status`, `anomaly_score`, `priority_score`), Decisões 1 e 2 registradas.

## Fase 2 — Fundação do repositório
**Entregas:** `pyproject.toml`, estrutura `src/`, `tests/`, `scripts/`, `dashboard/`, `data/`, `.env.example`, `.gitignore`, `Makefile`, logging/config básicos, DDL DuckDB inicial.  
**Aceite:** instalação local funciona; `pytest` smoke roda; config carrega.

## Fase 3 — Dados sintéticos e ground truth
**Entregas:** gerador seedado de 6 fontes; cenários normais e problemáticos; ground truth separado.  
**Aceite:** validações de coerência passam; cenários obrigatórios presentes.

## Fase 4 — Ingestão, Bronze e Silver
**Entregas:** leitores CSV/Excel, validação de schema, quarentena, manifesto por `run_id`, tabelas Silver.  
**Aceite:** contagens auditadas; inválidos isolados; reexecução idempotente.

## Fase 5 — Conciliação determinística
**Entregas:** engine R1-R6, matcher controlado, `gold_reconciliation_cases/divergences`, auditoria.  
**Aceite:** testes unitários por regra; sem auto-match ambíguo; evidência rastreável.

## Fase 6 — Inteligência de exceções
**Entregas:** features, MAD/IQR, Isolation Forest, comparação, `gold_anomaly_scores`, `gold_case_priority`.  
**Aceite:** métricas com ground truth (precision/recall/F1/Precision@K); reason codes explicáveis.

## Fase 7 — Briefing e feedback
**Entregas:** `TemplateProvider`, `ExplanationProvider` interface, `gold_case_briefs`, `gold_analyst_feedback`.  
**Aceite:** briefing grounded/assistivo; feedback persistido; sem LLM no caminho crítico.

## Fase 8 — Dashboard e exports
**Entregas:** Streamlit com KPIs, fila priorizada, drill-down, feedback; exports CSV/Excel/HTML.  
**Aceite:** demo ponta a ponta; exports consistentes com Gold.

## Fase 9 — Testes, métricas e hardening
**Entregas:** testes unitários/integração, baseline manual simulado, medição de KPIs, revisão de logs.  
**Aceite:** suite verde; métricas reportadas; execução limpa em ambiente novo.

## Fase 10 — Documentação final
**Entregas:** README técnico de execução, limitações, evolução cloud, checklist de demo.  
**Aceite:** terceiro consegue executar localmente seguindo documentação.