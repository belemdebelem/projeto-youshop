# Escopo Funcional do MVP

## Foco
Exclusivo em **Financeiro e Controladoria**: conciliação, consolidação, rastreabilidade, priorização de exceções e apoio à decisão.

## Funcionalidades incluídas
1. **Geração de dados sintéticos** com cenários normais e problemáticos + ground truth.
2. **Ingestão e validação** de CSV/Excel, com quarentena e manifesto de arquivos.
3. **Camadas Bronze/Silver/Gold** em DuckDB com rastreabilidade por `run_id`.
4. **Conciliação determinística R1-R6** com evidências e status.
5. **Detecção e priorização de exceções**: MAD/IQR + Isolation Forest comparado, `anomaly_score`, `financial_severity`, `urgency_score`, `priority_score`.
6. **Briefing investigativo grounded** via `TemplateProvider` (default) e interface plugável para LLM futura.
7. **Dashboard Streamlit** com KPIs, fila priorizada, drill-down, evidências e feedback do analista.
8. **Exports** CSV/Excel/HTML (conciliação, divergências, anomalias, resumo gerencial).
9. **Auditoria**: runs, manifesto, erros, versão de regras/modelo/config.
10. **Testes e métricas**: regras financeiras, pipeline e avaliação de anomalias (precision/recall/F1/Precision@K).

## Fora do escopo
- Integrações reais com YouShop.
- Cloud, orquestradores distribuídos, infraestrutura pesada.
- LLM obrigatória, chatbot, decisões autônomas.
- Ações irreversíveis (pagamentos, bloqueios, ajustes automáticos).
- Domínios fora de Finanças/Controladoria.

## Critérios de aceite
- Pipeline roda localmente ponta a ponta com comando documentado.
- Casos conciliados/divergentes rastreáveis até registros de origem.
- Divergência financeira e anomalia estatística apresentadas separadamente.
- Fila de investigação ordenada por prioridade transparente e explicável.
- Briefings citam evidências/IDs e são rotulados como assistivos.
- Exports gerados e consistentes com os dados Gold.
- Testes e métricas executáveis em ambiente local.