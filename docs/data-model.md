# Modelo de Dados

## Princípios
- Valores monetários em `Decimal` (sem float implícito em regras financeiras).
- Datas em ISO 8601.
- Toda saída analítica carrega `run_id` para rastreabilidade.
- Identificadores de origem preservados (IDs de fonte).

## Bronze / Raw (entrada)
| Tabela | Campos-chave |
|---|---|
| `raw_sales` | `sale_id`, `order_id`, `producer_id`, `creator_id`, `gross_amount`, `platform_fee`, `net_amount`, `sale_date`, `status`, `source_file` |
| `raw_gateway_payments` | `payment_id`, `order_id`, `sale_id`, `amount_captured`, `payment_date`, `status`, `gateway_ref`, `source_file` |
| `raw_commissions` | `commission_id`, `sale_id`, `creator_id`, `commission_rate`, `expected_commission`, `status`, `source_file` |
| `raw_producer_receivables` | `receivable_id`, `sale_id`, `producer_id`, `amount_due`, `due_date`, `status`, `source_file` |
| `raw_payouts` | `payout_id`, `beneficiary_type`, `beneficiary_id`, `reference_id`, `amount_paid`, `payout_date`, `status`, `source_file` |
| `raw_refunds_chargebacks` | `event_id`, `sale_id`, `payment_id`, `amount`, `event_date`, `event_type`, `reason`, `source_file` |

## Silver (padronizado)
Campos comuns adicionais:
- `ingested_run_id`
- `record_hash`
- `is_valid`
- `validation_errors` (JSON/texto estruturado)
- `normalized_at`

Tabelas:
- `silver_sales`
- `silver_gateway_payments`
- `silver_commissions`
- `silver_producer_receivables`
- `silver_payouts`
- `silver_refunds_chargebacks`
- `silver_rejects`

## Gold (analítico/auditável)
| Tabela | Objetivo | Campos principais |
|---|---|---|
| `gold_reconciliation_cases` | Fonte de verdade da conciliação | `case_id`, `run_id`, `case_type`, `entity_a_type`, `entity_a_id`, `entity_b_type`, `entity_b_id`, `expected_amount`, `actual_amount`, `diff_amount`, `reconciliation_status`, `match_rule`, `confidence`, `evidence_json`, `created_at` |
| `gold_divergences` | Casos não conciliados/relevantes | derivado de `gold_reconciliation_cases` + severidade e valor |
| `gold_anomaly_scores` | Sinal de atipicidade | `anomaly_id`, `run_id`, `entity_type`, `entity_id`, `model_name`, `model_version`, `anomaly_score`, `baseline_context_json`, `is_anomaly`, `reason_codes`, `feature_snapshot_json`, `created_at` |
| `gold_case_priority` | Fila priorizada | `case_id`, `run_id`, `financial_severity`, `anomaly_score`, `urgency_score`, `priority_score`, `priority_reason`, `created_at` |
| `gold_case_briefs` | Briefing grounded | `brief_id`, `case_id`, `run_id`, `provider` (`template`/`llm_optional`), `brief_text`, `evidence_refs_json`, `is_assistive`, `created_at` |
| `gold_analyst_feedback` | Decisão humana | `feedback_id`, `case_id`, `run_id`, `analyst_label`, `cause_code`, `notes`, `decided_at`, `decided_by` |
| `gold_kpis` | KPIs por execução/período | `kpi_id`, `run_id`, `period`, `metric_name`, `metric_value`, `metadata_json` |

## Auditoria
| Tabela | Objetivo |
|---|---|
| `audit_runs` | `run_id`, início/fim, status, `rules_version`, `model_version`, `config_hash`, resumo |
| `audit_file_manifest` | arquivo, hash, `rows_read`, `rows_valid`, `rows_rejected`, `source_layer` |
| `audit_errors` | etapa, entidade, severidade, mensagem, contexto |
| `audit_model_runs` | algoritmo, hiperparâmetros, features, seed, hash de dataset, métricas |

## Relacionamentos principais
- `sale_id/order_id` conectam vendas, pagamentos, comissões, recebíveis, payouts e eventos.
- `beneficiary_type + beneficiary_id + reference_id` conectam payouts a referências de origem.
- `gold_case_priority.case_id` referencia `gold_reconciliation_cases.case_id`.
- `gold_case_briefs.case_id` referencia `gold_reconciliation_cases.case_id`.
- `gold_analyst_feedback.case_id` referencia `gold_reconciliation_cases.case_id`.
- `gold_anomaly_scores.entity_id` pode ser associado a casos quando aplicável (por chave de negócio).