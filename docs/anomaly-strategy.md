# Estratégia de Anomalias e Priorização

## Objetivo
Identificar e priorizar exceções financeiras para investigação, sem substituir a conciliação determinística.

## Separação conceitual
- `reconciliation_status`: fato financeiro objetivo (fonte de verdade).
- `anomaly_score`: atipicidade estatística/ML (não é probabilidade de fraude).
- `financial_severity`: gravidade por impacto financeiro e criticidade do caso.
- `urgency_score`: urgência operacional (idade, recorrência, pendência).
- `priority_score`: ordenação final da fila de investigação.

## Camadas
### A1 — Baseline estatístico (obrigatório)
- Técnicas: MAD/IQR, medianas e razões por grupo comparável (`producer_id`, `creator_id`, `event_type`, período).
- Uso: explicabilidade, baseline e fallback.

### A2 — ML multivariado (candidato principal)
- Técnica: Isolation Forest (scikit-learn), atrás de interface comum (`AnomalyDetector`).
- Entrada: features numéricas/categóricas codificadas com snapshot auditável.
- Saída: `anomaly_score`, `is_anomaly`, `reason_codes`, `feature_snapshot_json`.

### A3 — Regras de contexto
- Reforçam prioridade por recorrência, atraso, valor alto, duplicidades e eventos críticos.

## Features candidatas
- `amount`, `diff_amount_abs`
- `amount_vs_group_median`, `amount_vs_group_mad`
- `fee_rate_deviation`, `commission_rate_deviation`
- `days_to_payout`
- `entity_txn_frequency_7d`, `entity_txn_frequency_30d`
- `entity_divergence_count_30d`
- `is_refund_or_chargeback`
- `reconciliation_status_encoded`

**Regra:** `ground_truth` de anomalias não entra como feature.

## Fórmula de prioridade (transparente)
`priority_score = w1*financial_severity_norm + w2*anomaly_score_norm + w3*urgency_norm + critical_override`

- Pesos (`w1,w2,w3`) configuráveis e versionados.
- `critical_override` permite elevar casos críticos (ex.: duplicidade relevante) independentemente do ML.

## Avaliação obrigatória
- Comparar baseline MAD/IQR vs Isolation Forest em dataset sintético com ground truth.
- Métricas: precision, recall, F1 e **Precision@K** (foco da fila de investigação).
- Registrar taxa de falsos positivos e exemplos de erro por categoria.

## Guardrails
- Sem decisão automática de fraude/prejuízo.
- Sem auto-treinamento no runtime do MVP.
- Sem feedback humano usado para alterar modelo durante a execução atual (apenas registro para evolução futura).
- Explicações devem citar evidências observáveis (valores, grupos, desvios, IDs).