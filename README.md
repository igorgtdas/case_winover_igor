# AtlasShop Assist

Assistente conversacional interno para suporte e operações da AtlasShop — empresa fictícia de software para gestão de lojas online.

Construído com LangChain + Groq (LLaMA) + FastAPI. Interface via terminal chamando a API REST.

---

## Pré-requisitos

- Python 3.11+
- Conta Groq com chave de API: https://console.groq.com/keys
- Pacotes listados em `requirements.txt`

---

## Instalação

```bash
# 1. Clone o repositório ou copie os arquivos para uma pasta local

# 2. Crie e ative um ambiente virtual
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure o ambiente
cp .env.example .env
# Abra .env e preencha GROQ_API_KEY com sua chave

# 5. Crie o banco SQLite a partir dos CSVs (execute uma vez)
python setup_db.py
```

---

## Executando

### Iniciar o servidor FastAPI

```bash
uvicorn api:app --reload
```

O servidor sobe em `http://localhost:8000`.

### Usando a API pelo terminal (curl)

**Enviar uma mensagem:**
```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual a política de reembolso atual?", "session_id": "sessao-01"}'
```

**Ver histórico da sessão:**
```bash
curl -s http://localhost:8000/session/sessao-01/history
```

**Encerrar sessão:**
```bash
curl -s -X DELETE http://localhost:8000/session/sessao-01
```

**Health check:**
```bash
curl -s http://localhost:8000/health
```

### Documentação interativa da API

Com o servidor rodando, acesse no navegador:
- Swagger UI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

---

## Estrutura de arquivos

```
.
├── api.py                    # Servidor FastAPI — endpoints REST
├── orchestrator.py           # Controlador do fluxo conversacional
├── chat.py                   # Interface CLI alternativa (sem API)
├── setup_db.py               # Cria o banco SQLite a partir dos CSVs
├── requirements.txt
├── .env.example              # Template de variáveis de ambiente
│
├── agents/
│   ├── guard_agent.py        # Filtro de segurança e safety
│   ├── router_agent.py       # Classificador de intenção
│   ├── knowledge_agent.py    # Especialista em base de conhecimento
│   ├── data_agent.py         # Especialista em dados operacionais (SQL)
│   └── escalation_agent.py   # Avaliador de escalonamento
│
├── core/
│   ├── config.py             # Parâmetros de todos os agentes (carrega do .env)
│   ├── database.py           # Conexão SQLite via SQLAlchemy
│   └── knowledge_loader.py   # Carrega documentos .md da pasta knowledge/
│
├── tools/
│   ├── knowledge_tools.py    # Tools LangChain para consulta de documentos
│   └── sql_tools.py          # Tools LangChain para consulta SQL (SQLDatabaseToolkit)
│
├── knowledge/                # Base de conhecimento interna (arquivos .md)
│   ├── catalogo_planos.md
│   ├── comunicados_incidentes.md
│   ├── faq_atendimento.md
│   ├── playbook_escalonamento.md
│   ├── politica_cancelamento_reembolso_antiga.md
│   └── politica_cancelamento_reembolso_atual.md
│
└── data/                     # Dados operacionais (importados para SQLite)
    ├── clientes.csv
    ├── pedidos.csv
    └── reembolsos.csv
```

---

## Arquitetura e fluxo principal

```
Terminal / curl
      │
      ▼
  POST /chat  (FastAPI — api.py)
      │
      ▼
  Orchestrator.chat()
      │
      ├─ 1. GuardAgent       → segurança e safety
      │       ↓ block?       → retorna rejeição imediata
      │
      ├─ 2. RouterAgent      → classifica: knowledge | data | escalation
      │
      ├─ 3. Agente alvo
      │       ├─ KnowledgeAgent  → ReAct + tools (get_document, get_full_knowledge_base)
      │       ├─ DataAgent       → ReAct + SQL tools (list_tables, schema, query, checker)
      │       └─ EscalationAgent → direto (sem tools)
      │
      └─ 4. EscalationAgent  → se should_escalate=true, gera relatório estruturado
                                 e anexa ao final da resposta
```

Cada sessão (`session_id`) mantém um `Orchestrator` próprio com histórico independente.

---

## Configuração de parâmetros por agente

Todos os parâmetros ficam no `.env`. Nenhum agente precisa ser alterado no código para mudar temperatura, tokens ou janela de contexto.

| Variável | Descrição | Padrão |
|---|---|---|
| `GUARD_TEMPERATURE` | Criatividade do Guard (0 = determinístico) | `0` |
| `GUARD_MAX_TOKENS` | Limite de tokens na resposta do Guard | `256` |
| `GUARD_CONTEXT_WINDOW` | Turnos de histórico que o Guard recebe | `0` (stateless) |
| `ROUTER_CONTEXT_WINDOW` | Turnos que o Router considera para classificar | `5` |
| `KNOWLEDGE_TEMPERATURE` | Criatividade do KnowledgeAgent | `0.1` |
| `KNOWLEDGE_MAX_TOKENS` | Limite de tokens na resposta do Knowledge | `1024` |
| `KNOWLEDGE_CONTEXT_WINDOW` | Turnos de histórico do KnowledgeAgent | `5` |
| `DATA_CONTEXT_WINDOW` | Turnos de histórico do DataAgent | `5` |
| `ESCALATION_MAX_TOKENS` | Limite de tokens do relatório de escalonamento | `512` |

`CONTEXT_WINDOW=5` significa que o agente recebe as últimas 5 perguntas + 5 respostas (10 mensagens) do histórico. `CONTEXT_WINDOW=0` desativa a memória (agente stateless).

Padrão para todos os agentes: `TOP_P=1.0` (nucleus sampling desativado).

---

## Modelos usados

| Agente | Modelo padrão | Justificativa |
|---|---|---|
| Guard | `llama-3.1-8b-instant` | Leve e rápido — roda antes de tudo |
| Router | `llama-3.1-8b-instant` | Classificação simples não exige modelo grande |
| Knowledge | `llama-3.3-70b-versatile` | Raciocínio robusto para interpretar documentos |
| Data | `llama-3.3-70b-versatile` | Geração de SQL + aplicação de regras de negócio |
| Escalation | `llama-3.3-70b-versatile` | Avaliação de regras complexas do playbook |

Todos os modelos são substituíveis via `.env` sem alterar código.

---

## Decisões técnicas e trade-offs

### Groq + LLaMA em vez de OpenAI
Groq oferece inferência muito rápida para os modelos LLaMA, gratuita nos tiers de desenvolvimento, e evita dependência de um único provedor. Trade-off: a Groq tem limites de rate mais apertados que a OpenAI em uso intenso.

### ReAct Agent para Knowledge e Data
Os dois agentes que precisam de raciocínio multi-etapa (consultar documento específico ou iterar em SQL) usam o padrão ReAct (Reason + Act). Os demais agentes (Guard, Router, Escalation) são simples cadeias LLM → parser, sem loop de ferramentas, para manter latência baixa.

### Janela de contexto por fatiamento de lista
Em vez de usar `ConversationBufferWindowMemory` do LangChain (que gerencia memória internamente), cada agente recebe o histórico completo do Orchestrator e fatia apenas os últimos N turnos antes de invocar o executor. Isso mantém o histórico central em um único lugar e dá controle independente por agente.

### SQLite local em vez de banco externo
Simples de subir sem infraestrutura adicional. Para produção, basta trocar a connection string em `core/database.py` para PostgreSQL ou outro banco — o SQLDatabaseToolkit funciona com qualquer banco suportado pelo SQLAlchemy.

### Sessões em memória (dicionário Python)
Funciona para um único worker/processo. Para múltiplos workers ou reinicialização do servidor, o histórico é perdido. O README e o código marcam os pontos exatos de substituição por Redis ou banco.

### Parsing por regex em vez de output parser estruturado
Os agentes ReAct produzem texto livre. A instrução de formato fica no system prompt, e o parsing extrai os campos com regex simples. É frágil se o modelo não seguir o formato, mas evita adicionar uma segunda chamada LLM só para estruturar a saída. Os TODOs no código indicam onde adicionar fallbacks.

---

## Limitações conhecidas

- Sessões não sobrevivem ao restart do servidor (armazenamento em memória)
- Parsing de saída dos agentes ReAct baseado em regex pode falhar se o modelo não seguir o formato instruído
- Sem autenticação nos endpoints (marcado como TODO em `api.py`)
- `top_p` não é passado diretamente ao `ChatGroq` (precisa de `model_kwargs`) — está comentado nos agentes como TODO
