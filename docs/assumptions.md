# Assunções e Limites do MVP

## Assunções de negócio e dados
- Não há acesso a dados reais da YouShop; os dados serão **sintéticos, coerentes e realistas**.
- As fontes simuladas representam domínios de Finanças/Controladoria: vendas, gateway, comissões, recebíveis, payouts/saques e estornos/chargebacks.
- IDs, datas e status podem variar por fonte, exigindo padronização no Silver.
- Ground truth sintético será gerado para validação de regras e avaliação de anomalias, mas **não será usado como feature** no modelo.

## Assunções técnicas
- Execução 100% local em máquina convencional.
- DuckDB será o banco analítico padrão (arquivo local).
- Pandas é suficiente para volume de dados do MVP.
- Reprocessamento por `run_id` é idempotente e preserva histórico.

## Limites do MVP
- Sem integrações com sistemas reais, APIs externas obrigatórias ou cloud.
- Sem decisões financeiras autônomas (não pagar, não bloquear, não ajustar valores).
- GenAI não é obrigatória; `TemplateProvider` é padrão. `LLMProvider` é apenas interface/futuro opcional.
- Feedback do analista é registrado para auditoria/avaliação, sem retraining automático.
- Modelos de anomalia podem gerar falsos positivos; métricas e explicabilidade são obrigatórias.

## Evolução futura (documentada, fora do MVP)
- Integração com fontes reais (ERP/gateway/financeiro).
- Orquestração agendada e monitoramento em cloud/data platform.
- Camada de causa raiz supervisionada com histórico rotulado.
- Provider LLM opcional com mascaramento e política de privacidade formal.