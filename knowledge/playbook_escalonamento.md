# Playbook de Escalonamento
**Documento:** playbook_escalonamento  
**Versão:** 1.7  
**Última atualização:** 2026-02-02  
**Status:** vigente

## Quando escalar para atendimento humano
Escalar quando houver pelo menos uma das condições abaixo:

1. cliente do plano Enterprise com risco operacional ou financeiro;
2. suspeita de fraude ou pedido em `fraud_review`;
3. pagamento em `chargeback`;
4. solicitação fora da política, mas com possível exceção comercial;
5. menção a ação judicial, órgão regulador ou ameaça pública relevante;
6. indisponibilidade crítica sem comunicado conclusivo;
7. divergência entre base documental e dado operacional;
8. tentativa de novo reembolso para pedido que já possui solicitação em andamento.

## Níveis sugeridos
- **L1 / suporte operacional:** dúvidas simples, status de pedido, orientação baseada em FAQ.
- **L2 / operações:** conflitos de regra, cancelamento sensível, casos financeiros não triviais.
- **Financeiro:** cobrança duplicada confirmada, estorno, reconciliação.
- **Risco:** fraude, chargeback, identidade ou comportamento suspeito.

## Boas práticas
- Registrar qual condição disparou o escalonamento.
- Informar a última evidência encontrada.
- Evitar respostas categóricas quando houver incerteza relevante.
