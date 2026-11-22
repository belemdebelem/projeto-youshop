# Regras de Conciliação Determinística

## Princípios
- Regras versionadas, explícitas e testáveis.
- Tolerância monetária explícita (`R$0,01`) salvo regra específica.
- Valores em `Decimal`.
- Sem auto-conciliação ambígua.
- Todo resultado registra `match_rule`, `confidence`, evidência e origem.

## Catálogo de regras

### R1 — Venda × Gateway Payment
- **Chave preferencial:** `sale_id` (fallback `order_id`).
- **Regra:** `abs(gateway.amount_captured - sale.gross_amount) <= 0.01`.
- **Status:** `matched`, `amount_mismatch`, `missing_payment`, `missing_sale`, `duplicate_payment`.
- **Observação:** múltiplos pagamentos para o mesmo contexto exigem análise explícita; duplicidade de negócio marcada quando aplicável.

### R2 — Comissão esperada × Comissão registrada
- **Base:** `expected_commission = gross_amount * commission_rate` (ou fórmula configurada por regra de negócio).
- **Regra:** diferença absoluta dentro da tolerância definida.
- **Status:** `matched`, `commission_mismatch`, `missing_commission`, `duplicate_commission`.

### R3 — Devido (produtor/creator) × Payout
- **Chave forte:** `beneficiary_type + beneficiary_id + reference_id`.
- **Regra exata:** valores iguais dentro da tolerância.
- **Regra controlada (sem chave forte):** candidato por `beneficiary + valor exato + janela temporal` (ex.: ±3 dias), apenas se houver **candidato único**.
- **Status:** `matched`, `pending_payout`, `amount_mismatch`, `missing_payout`, `duplicate_payout`, `ambiguous_match`.
- **Proibição:** se houver >1 candidato viável, marcar `ambiguous_match` (sem conciliação automática).

### R4 — Estorno/Chargeback × Venda/Pagamento
- **Regra:** evento negativo deve referenciar origem válida (`sale_id/payment_id`); valor não pode exceder capturado aplicável.
- **Status:** `matched`, `orphan_event`, `amount_mismatch`.

### R5 — Integridade de registro
- **Verifica:** campos obrigatórios, domínio de status, datas válidas, sinal válido, consistência `gross-fee-net`.
- **Resultado:** registros inválidos vão para `silver_rejects` com `reconciliation_status = invalid_record`.

### R6 — Duplicidade
- **Duplicidade técnica:** mesmo `record_hash`.
- **Duplicidade de negócio:** mesma chave natural/ID externo com conflito semântico.
- **Status:** `technical_duplicate`, `business_duplicate`.

## Regras de severidade (para priorização financeira)
- **Crítica:** duplicidade de pagamento/impacto alto, evento órfão relevante, divergência de valor elevado acima de limiar configurado.
- **Alta:** `amount_mismatch`, `missing_payout` com impacto financeiro relevante.
- **Média:** `pending_payout`, divergências menores com padrão recorrente.
- **Baixa:** pendências de baixo impacto e sem risco imediato.

Os limiares numéricos devem ser configuráveis e versionados em `config`.

## Rastreabilidade obrigatória
Cada caso deve armazenar:
- `case_id`, `run_id`, `case_type`
- entidades comparadas e IDs de origem
- `expected_amount`, `actual_amount`, `diff_amount`
- `match_rule`, `confidence`
- `evidence_json` (campos usados, tolerância, janela temporal, candidatos descartados resumidos)