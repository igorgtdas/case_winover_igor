# Política de Cancelamento e Reembolso
**Documento:** politica_cancelamento_reembolso  
**Versão:** 2.1  
**Última atualização:** 2026-01-12  
**Status:** vigente

## Regras gerais

### Cancelamento
- Assinaturas mensais podem ser canceladas a qualquer momento.
- Assinaturas anuais podem ser canceladas a qualquer momento, mas o tratamento financeiro depende das regras abaixo.
- Cancelamento encerra a renovação futura, mas não retroage automaticamente cobranças já processadas.

### Reembolso por arrependimento
- Para primeira contratação, existe janela de arrependimento de **7 dias corridos** após a ativação.
- Dentro da janela, o reembolso pode ser integral, desde que o pagamento esteja aprovado e não exista indício de fraude.
- Após 7 dias, não há reembolso automático por arrependimento.

### Reembolso em caso de cobrança duplicada
- Cobrança duplicada confirmada pode gerar reembolso integral da cobrança excedente.
- Casos com múltiplas tentativas de pagamento devem ser verificados contra o status operacional antes de qualquer decisão.

### Plano anual
- Após a janela de 7 dias, o cancelamento do plano anual não gera reembolso automático proporcional.
- Exceções comerciais só podem ser analisadas por atendimento humano.

### Fraude e contestação
- Pedidos em `fraud_review` ou com pagamento `chargeback` não podem receber aprovação automática de reembolso.
- O assistente deve orientar escalonamento nesses casos.

### Reembolso já iniciado
- Se já existir solicitação de reembolso em andamento para o pedido, o assistente deve informar o status atual e evitar duplicidade de nova abertura.

## Respostas esperadas
Boas respostas normalmente combinam:
- regra da política;
- situação atual do pedido;
- eventual status de reembolso já existente.
