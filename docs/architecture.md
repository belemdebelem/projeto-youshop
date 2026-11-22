# Arquitetura Técnica — Financial Intelligence & Reconciliation Platform

## Visão geral
Solução local para **Finanças e Controladoria** que transforma dados financeiros dispersos em casos conciliados, priorizados e investigáveis. O diferencial é a combinação de **conciliação determinística** (fonte de verdade) com **inteligência de exceções** (ML + priorização explicável + briefing grounded).

## Diagrama
```text
FONTES SINTÉTICAS (CSV/Excel)
Vendas | Pagamentos/Gateway | Comissões | Recebíveis Produtor | Payouts/Saques | Estornos/Chargebacks
                                        |
                                        v
                           [INGESTÃO + VALIDAÇÃO]  Python/Pandas
                           schema, tipos, domínio, hash, quarentena, manifesto
                                        |
                                        v
                     [BRONZE - imutável por run_id]  data/bronze/<run_id>/ + manifest.json
                                        |
                                        v
                     [SILVER - limpo/padronizado]  DuckDB: silver_*, silver_rejects
                                        |
                    +-------------------+-------------------+
                    |                                       |
                    v                                       v
      [CONCILIAÇÃO DETERMINÍSTICA]              [PERFIL ESTATÍSTICO/BASELINE]
      R1-R6, match exato/controlado,            MAD/IQR por grupo comparável
      status, diff, evidência, origem           desvios, taxas, recorrência
                    |                                       |
                    +-------------------+-------------------+
                                        v
                          [INTELIGÊNCIA DE EXCEÇÕES]
                 anomaly_score (IF + baseline)  |  financial_severity
                 reason_codes/evidências         |  urgency/recorrência
                                        |
                                        v
                          [PRIORIZAÇÃO TRANSPARENTE]
                    priority_score = w1*fin + w2*anom + w3*urg + override
                                        |
                                        v
                          [BRIEFING INVESTIGATIVO]
                    TemplateProvider (default, offline)
                    LLMProvider (opcional futuro, fora do caminho crítico)
                                        |
                                        v
                     [GOLD - DuckDB analítico/auditável]
        reconciliation_cases | divergences | anomaly_scores
        case_priority        | case_briefs | analyst_feedback
        kpis | audit_runs | audit_manifest | audit_errors | audit_model_runs
                                        |
                    +-------------------+-------------------+
                    |                                       |
                    v                                       v
            [STREAMLIT DASHBOARD]                   [EXPORTS / AUDITORIA]
      KPIs, fila por prioridade, drill-down      CSV / Excel / HTML
      briefing, evidências, feedback             histórico por run_id
```

## Componentes
| Componente | Responsabilidade | Tecnologia |
|---|---|---|
| Ingestão/Validação | Ler fontes, validar schema/domínio, gerar hash, quarentena | Python, Pandas |
| Bronze | Preservar raw imutável por execução + manifesto | FS + JSON/CSV |
| Silver | Padronizar, deduplicar, tipar, carregar tabelas limpas | DuckDB |
| Reconciliação | Aplicar R1-R6, gerar status/diff/evidência | Python + SQL/DuckDB |
| Inteligência de Exceções | Baseline MAD/IQR, Isolation Forest, reason codes | scikit-learn, Pandas |
| Priorização | Calcular prioridade transparente e explicável | Python/DuckDB |
| Briefing | Gerar resumo grounded assistivo | TemplateProvider; interface LLM futura |
| Gold/Auditoria | Persistir casos, KPIs, auditoria, feedback | DuckDB |
| Dashboard | Investigar fila, KPIs e exports | Streamlit |

## Invariantes
- **Determinístico no financeiro:** ML/GenAI não alteram `reconciliation_status`, valores ou match.
- **Rastreabilidade:** todo caso tem `run_id`, IDs de origem e evidência.
- **Idempotência:** reprocessamento não corrompe histórico; resultados versionados por execução.
- **Offline-first:** MVP executa sem API externa.
- **Sem autonomia financeira:** nenhuma ação irreversível automática.

## Estrutura de diretórios alvo
```text
projeto-youshop/
  docs/
  data/{raw,bronze,exports,duckdb}/
  src/youshop_finance/
    ingestion/ transform/ reconciliation/ intelligence/ reporting/ storage/ pipeline/
  scripts/
  dashboard/
  tests/{unit,integration,fixtures}/
  pyproject.toml Makefile .env.example
```