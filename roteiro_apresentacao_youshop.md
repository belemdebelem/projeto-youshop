# Roteiro simples — Desafio de Inovação YouShop

Apresentação de 9 slides, estimada em 4 a 5 minutos. O roteiro acompanha o arquivo editável `apresentacao_youshop_editavel.pptx`.

## Slide 1 — Apresentação pessoal

**Este slide é seu.** Preencha os campos com seu nome, o que faz, o que te move e por que a oportunidade na YouShop conversa com sua trajetória. Conte uma experiência verdadeira que ajude a explicar por que você se interessou por este problema. Não precisa ser uma experiência profissional.

## Slide 2 — O problema

“Escolhi olhar para a conferência financeira. Uma venda pode aparecer em várias fontes: vendas, gateway, comissões, repasses, saques e estornos. Quando os registros não batem, alguém precisa cruzar essas informações e entender o que aconteceu. Isso pode tornar o fechamento mais lento e dificultar a localização de divergências.”

## Slide 3 — Quem sente o problema

“Esse trabalho afeta principalmente duas áreas. O Financeiro precisa conferir pagamentos e repasses. A Controladoria precisa consolidar informações para produzir indicadores confiáveis. Como não tenho acesso a dados internos, representei esse fluxo com dados sintéticos, sem apresentá-los como resultados reais da YouShop.”

## Slide 4 — A solução

“Minha proposta é o Radar Financeiro. O protótipo recebe arquivos de seis fontes, valida e padroniza os registros e aplica regras para comparar vendas, pagamentos, comissões, repasses e estornos. Depois, organiza os casos para investigação em um dashboard, com as evidências que explicam cada divergência.”

## Slide 5 — O papel da IA

“As regras determinísticas fazem as comparações financeiras reproduzíveis. A IA, por meio do Isolation Forest, procura operações que pareçam atípicas em relação aos padrões dos dados e ajuda a priorizar a análise. Esse sinal não significa fraude: uma pessoa revisa o caso, e o modelo não altera valores nem toma decisões financeiras.”

## Slide 6 — Demonstração do protótipo

“Este é o espaço para mostrar o dashboard. Na primeira captura, vou apresentar os indicadores e a distribuição dos casos. Na segunda, vou abrir uma divergência, mostrar os registros relacionados e explicar como a fila e o briefing ajudam a investigação.”

**Antes de apresentar:** substitua os quadros do slide por screenshots reais do dashboard. Prefira capturas sem dados pessoais; o protótipo usa dados sintéticos.

## Slide 7 — Alternativas

“Considerei um painel com planilhas, uma solução apenas com regras, uma LLM obrigatória e uma infraestrutura em nuvem. Para o MVP, escolhi combinar regras com detecção de anomalias e manter a execução local. Assim, demonstro a análise inteligente sem deixar cálculos financeiros críticos nas mãos de um modelo generativo nem depender de serviços externos.”

## Slide 8 — Como medir

“Para avaliar se a solução funciona, precisamos medir a proporção de casos conciliados, o tempo do processamento, a qualidade da fila de anomalias e o volume financeiro das divergências. O dashboard já mostra conciliação, divergências, valores e anomalias sinalizadas. Ainda falta calcular as métricas de qualidade do modelo e comparar o tempo com um processo manual simulado; por isso, não apresento ganhos como se já tivessem sido comprovados.”

## Slide 9 — Limites e encerramento

“O protótipo usa dados sintéticos e não está conectado aos sistemas reais da YouShop. O modelo pode gerar falsos positivos e precisa de revisão humana. Ele não paga, bloqueia nem ajusta transações. A proposta é ajudar as equipes a encontrar e investigar exceções com mais clareza. Obrigado.”
