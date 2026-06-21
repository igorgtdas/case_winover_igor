# Cenário — AtlasShop Assist

A AtlasShop é uma empresa fictícia de software para gestão de lojas online.
O time de suporte e operações atende clientes dos planos Essencial, Pro e Enterprise.

Você recebeu uma base pequena de documentos internos e uma fonte estruturada com dados operacionais.
Use esse material para construir uma solução conversacional mínima funcional.

## Contexto de uso do assistente

O assistente será usado internamente por times de suporte/operações para:

- responder perguntas com base em documentação interna;
- consultar informações operacionais sobre clientes, pedidos e reembolsos;
- apoiar o time em situações que exigem escalonamento;
- manter coerência básica durante a conversa.

## Observações sobre o material

- Alguns documentos podem estar desatualizados.
- Nem toda pergunta deve ser respondida apenas com base documental.
- Nem toda consulta operacional deve ignorar regras de negócio descritas nos documentos.
- Simplificações são aceitáveis, desde que estejam explícitas.

## Sugestões de uso

Você pode assumir que:
- os arquivos em `knowledge/` representam a base de conhecimento;
- os arquivos em `data/` representam dados operacionais consultáveis.

Você tem liberdade para definir a forma de ingestão, orquestração e resposta.
