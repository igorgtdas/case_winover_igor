# AtlasShop Assist

Assistente conversacional interno para suporte e operações da AtlasShop — empresa fictícia de software para gestão de lojas online.

Construído com LangChain + Groq (LLaMA) + FastAPI. Interface via terminal ou Postman chamando a API REST.

---

## Pré-requisitos

- Conta Groq com chave de API: https://console.groq.com/keys
- **Docker** (recomendado) — ou Python 3.11+ para rodar sem Docker

---

## Instalação e execução com Docker (recomendado)

A forma mais simples de rodar o projeto — não exige Python, pip ou venv instalados.

```bash
# 1. Clone o repositório
git clone <url-do-repo>
cd Case_winover

# 2. Configure o ambiente
cp .env.example .env
# Abra .env e preencha GROQ_API_KEY com sua chave

# 3. Suba o container
docker compose up --build
```

O servidor sobe em `http://localhost:8000`.

O banco SQLite é criado automaticamente dentro do container na primeira execução. Os dados ficam em um volume Docker e sobrevivem a `docker stop` / `docker start`.

**Comandos úteis:**

```bash
docker compose up --build    # primeira vez (build + start)
docker compose up            # próximas vezes (sem rebuild)
docker compose down          # para e remove o container
docker compose logs -f       # acompanha os logs em tempo real
```

---

## Instalação sem Docker (alternativa)

```bash
# 1. Crie e ative um ambiente virtual
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure o ambiente
cp .env.example .env
# Abra .env e preencha GROQ_API_KEY com sua chave

# 4. Crie o banco SQLite a partir dos CSVs (execute uma vez)
python setup_db.py

# 5. Suba o servidor
uvicorn api:app --reload
```

> A tabela `escalation_logs` é criada automaticamente na primeira vez que um escalonamento ocorre.

O servidor sobe em `http://localhost:8000`.

---

## Usando a API

### Via documentação interativa (recomendado para testes)

Acesse no navegador com o servidor rodando:

```
http://localhost:8000/docs
```

Interface Swagger gerada automaticamente — permite testar todos os endpoints sem instalar nada.

---

### Via Postman

**1. Iniciar sessão (Start State)**

| Campo | Valor |
|---|---|
| Método | `POST` |
| URL | `http://localhost:8000/session/start` |
| Header | `Content-Type: application/json` |

Body (raw → JSON):
```json
{
  "session_id": "sessao-01",
  "user_name": "João Silva",
  "user_email": "joao@atlasshop.com",
  "plano": "Enterprise"
}
```

**2. Enviar mensagem**

| Campo | Valor |
|---|---|
| Método | `POST` |
| URL | `http://localhost:8000/chat` |
| Header | `Content-Type: application/json` |

Body (raw → JSON):
```json
{
  "message": "qual a política de reembolso vigente?",
  "session_id": "sessao-01"
}
```

**3. Ver histórico da sessão**

| Campo | Valor |
|---|---|
| Método | `GET` |
| URL | `http://localhost:8000/session/sessao-01/history` |

**4. Encerrar sessão**

| Campo | Valor |
|---|---|
| Método | `DELETE` |
| URL | `http://localhost:8000/session/sessao-01` |

**5. Health check**

| Campo | Valor |
|---|---|
| Método | `GET` |
| URL | `http://localhost:8000/health` |

---

### Via terminal (curl)

```bash
# 1. Iniciar sessão com contexto
curl -s -X POST http://localhost:8000/session/start \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s01","user_name":"Ana","user_email":"ana@atlasshop.com","plano":"Pro"}'

# 2. Enviar pergunta sobre documentação
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"qual a janela de reembolso vigente?","session_id":"s01"}' \
  | python -m json.tool

# 3. Consultar dados operacionais
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"qual o status do pedido P1008?","session_id":"s01"}' \
  | python -m json.tool

# 4. Encerrar sessão
curl -s -X DELETE http://localhost:8000/session/s01
```

> `| python -m json.tool` formata o JSON de resposta para facilitar a leitura.

---

## Endpoints disponíveis

| Método | Endpoint | O que faz |
|---|---|---|
| `POST` | `/session/start` | Inicia sessão com contexto (user_name, user_email, plano) |
| `POST` | `/chat` | Envia mensagem e recebe resposta |
| `GET` | `/session/{id}/history` | Retorna histórico + contexto da sessão |
| `DELETE` | `/session/{id}` | Encerra e limpa a sessão |
| `GET` | `/health` | Verifica status da API |

> `/session/start` é opcional. Usar `/chat` diretamente funciona, mas sem o contexto personalizado (plano, nome do atendente).

---

## Estrutura de arquivos

```
.
├── Dockerfile                  # Imagem Docker do projeto
├── docker-compose.yml          # Sobe o container com um comando
├── .dockerignore               # Exclui .venv, .env, __pycache__ da imagem
├── api.py                      # Servidor FastAPI — endpoints REST
├── orchestrator.py             # Controlador do fluxo conversacional
├── chat.py                     # Interface CLI alternativa (sem API)
├── setup_db.py                 # Cria o banco SQLite a partir dos CSVs
├── requirements.txt
├── .env.example                # Template de variáveis de ambiente
│
├── agents/
│   ├── guard_agent.py          # Filtro de segurança e safety
│   ├── router_agent.py         # Classificador de intenção
│   ├── knowledge_agent.py      # Especialista em base de conhecimento (chain direta)
│   ├── data_agent.py           # Especialista em dados SQL (dois passos: gera SQL → interpreta)
│   └── escalation_agent.py     # Avaliador de escalonamento
│
├── core/
│   ├── config.py               # Parâmetros de todos os agentes (carrega do .env)
│   ├── database.py             # Conexão SQLite via SQLAlchemy
│   ├── knowledge_loader.py     # Carrega documentos .md da pasta knowledge/
│   ├── session_context.py      # Start State — variáveis iniciais da sessão
│   ├── escalation_log.py       # Registro de escalonamentos no banco
│   ├── rate_limit.py           # Tratamento de RateLimitError do Groq (429)
│   └── trace.py                # Modelo ToolCall — rastreamento de chamadas de tools
│
├── tools/
│   ├── knowledge_tools.py      # Tools LangChain para consulta de documentos
│   ├── sql_tools.py            # Tools LangChain (SQLDatabaseToolkit)
│   └── clock_tool.py           # Retorna data/hora atual no fuso de Brasília
│
├── knowledge/                  # Base de conhecimento interna (arquivos .md)
│   ├── catalogo_planos.md
│   ├── comunicados_incidentes.md
│   ├── faq_atendimento.md
│   ├── playbook_escalonamento.md
│   ├── politica_cancelamento_reembolso_antiga.md
│   └── politica_cancelamento_reembolso_atual.md
│
└── data/                       # Dados operacionais (importados para SQLite)
    ├── clientes.csv
    ├── pedidos.csv
    └── reembolsos.csv
```

---

## Arquitetura e fluxo principal

```
Postman / curl / terminal
        │
        ▼
POST /session/start  →  cria SessionContext (user_name, user_email, plano)
        │
POST /chat
        │
        ▼
  Orchestrator.chat()
        │
        ├─ 1. GuardAgent         → segurança e safety
        │       ↓ block?         → retorna mensagem padrão de rejeição
        │
        ├─ 2. RouterAgent        → classifica: knowledge | data | escalation
        │
        ├─ 3. Agente alvo
        │       ├─ KnowledgeAgent  → chain direta: prompt + docs no contexto → LLM
        │       ├─ DataAgent       → gera SQL → executa → LLM interpreta resultado
        │       └─ EscalationAgent → chain direta (roteado diretamente pelo Router)
        │
        └─ 4. Se should_escalate=true:
                ├─ EscalationAgent gera relatório JSON
                ├─ registrar_escalamento() salva em escalation_logs no banco
                └─ Usuário recebe mensagem padrão (não vê detalhes internos)
```

---

## Start State — contexto inicial da sessão

Antes de enviar a primeira mensagem, chame `/session/start` com:

| Campo | Tipo | Descrição |
|---|---|---|
| `session_id` | string | ID único da conversa |
| `user_name` | string | Nome do atendente |
| `user_email` | string | Email do atendente (auditoria) |
| `plano` | string | `Essencial`, `Pro` ou `Enterprise` |

Esses dados são injetados automaticamente no prompt de cada agente durante toda a conversa. Clientes `Enterprise` recebem destaque de prioridade alta nas respostas.

---

## Escalonamento

Quando um agente detecta uma situação que requer atendimento humano (fraude, chargeback, exceção comercial, etc.):

1. **O usuário recebe** uma mensagem neutra:
   > *"Infelizmente não consigo atender a essa solicitação pelo assistente. Sua situação foi registrada e será encaminhada para o time responsável."*

2. **O banco registra** automaticamente na tabela `escalation_logs`:

| Coluna | Descrição |
|---|---|
| `created_at` | Timestamp UTC ISO 8601 |
| `session_id` | ID da sessão |
| `user_id` | ID do usuário |
| `user_name` | Nome do atendente (do Start State) |
| `user_email` | Email do atendente (do Start State) |
| `plano` | Plano do cliente (do Start State) |
| `nivel` | `L1`, `L2`, `Financeiro` ou `Risco` |
| `motivo` | Motivo objetivo do escalonamento |
| `evidencia` | Evidência que justificou |
| `proximos_passos` | Orientação para o time humano |
| `mensagem_usuario` | Mensagem original que disparou o escalonamento |
| `triggered_by` | `knowledge_agent`, `data_agent` ou `user` |

Para consultar os logs:
```sql
SELECT * FROM escalation_logs ORDER BY created_at DESC;
```

---

## LangSmith — observability e tracing

O LangSmith é a plataforma oficial de observability do LangChain. Com ele você visualiza cada chamada de LLM, tokens consumidos, latência e o trace completo de cada turno — incluindo as tools Python (`clock_tool`, `sql_query`).

### Configuração (3 passos)

**1. Crie uma conta e gere uma chave**

Acesse [smith.langchain.com](https://smith.langchain.com), crie uma conta gratuita e vá em **Settings → API Keys → Create API Key**.

**2. Adicione ao `.env`**

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_sua_chave_aqui
LANGSMITH_PROJECT=atlasshop-assist
```

> Para desativar o tracing sem remover as variáveis, mude para `LANGSMITH_TRACING=false`.

**3. Instale a dependência (já está no requirements.txt)**

```bash
pip install langsmith
```

Reinicie o servidor — nenhuma outra mudança é necessária.

### O que aparece no dashboard

Cada mensagem enviada via `POST /chat` gera um trace com a hierarquia completa:

```
RunnableSequence (ChatPromptTemplate | ChatGroq | StrOutputParser)
  ├─ [tool] clock_tool         input: {}  output: "22/06/2026"   ~0ms
  ├─ [tool] sql_query          input: {"sql": "SELECT ..."}      ~8ms
  │                            output: "('2026-06-12',)"
  ├─ ChatGroq (sql_chain)      512 tokens  →  142ms
  └─ ChatGroq (interpret_chain) 1.2k tokens →  891ms
```

| O que é rastreado | Detalhe |
|---|---|
| Prompt completo | system + histórico + input enviado ao modelo |
| Resposta bruta | saída do LLM antes do parser |
| Tokens | input / output / total por chamada |
| Latência | por etapa e total do turno |
| Tools Python | `clock_tool` e `sql_query` com input/output |
| Erros | stack trace completo quando algo falha |

### Avaliações automáticas (opcional)

No LangSmith você pode criar **datasets** com pares pergunta/resposta esperada e rodar **avaliadores** para medir qualidade ao longo do tempo — ex: "o SQL gerado é válido?", "a data calculada está correta?". Isso é feito na interface web sem alterar código.

---

## Configuração de parâmetros por agente

Todos os parâmetros ficam no `.env` — nenhum agente precisa ser alterado no código.

Cada agente tem uma variável `<AGENTE>_PROVIDER` que define qual LLM usar: `groq` (padrão) ou `openai`.

| Variável | Descrição | Padrão |
|---|---|---|
| `GUARD_PROVIDER` | Provider do Guard (`groq` ou `openai`) | `groq` |
| `GUARD_MODEL` | Modelo do Guard | `llama-3.1-8b-instant` |
| `GUARD_TEMPERATURE` | Criatividade (0 = determinístico) | `0` |
| `GUARD_MAX_TOKENS` | Limite de tokens na resposta | `256` |
| `GUARD_CONTEXT_WINDOW` | Turnos de histórico recebidos | `0` (stateless) |
| `ROUTER_PROVIDER` | Provider do Router (`groq` ou `openai`) | `groq` |
| `ROUTER_MODEL` | Modelo do Router | `llama-3.1-8b-instant` |
| `ROUTER_CONTEXT_WINDOW` | Turnos considerados para classificar | `5` |
| `KNOWLEDGE_PROVIDER` | Provider do KnowledgeAgent (`groq` ou `openai`) | `groq` |
| `KNOWLEDGE_MODEL` | Modelo do KnowledgeAgent | `llama-3.3-70b-versatile` |
| `KNOWLEDGE_TEMPERATURE` | Criatividade | `0.1` |
| `KNOWLEDGE_MAX_TOKENS` | Limite de tokens | `1024` |
| `KNOWLEDGE_CONTEXT_WINDOW` | Turnos de histórico | `5` |
| `DATA_PROVIDER` | Provider do DataAgent (`groq` ou `openai`) | `groq` |
| `DATA_MODEL` | Modelo do DataAgent | `llama-3.3-70b-versatile` |
| `DATA_TEMPERATURE` | Criatividade (0 = SQL preciso) | `0` |
| `DATA_MAX_TOKENS` | Limite de tokens | `1024` |
| `DATA_CONTEXT_WINDOW` | Turnos de histórico | `5` |
| `ESCALATION_PROVIDER` | Provider do EscalationAgent (`groq` ou `openai`) | `groq` |
| `ESCALATION_MODEL` | Modelo do EscalationAgent | `llama-3.3-70b-versatile` |
| `ESCALATION_MAX_TOKENS` | Limite de tokens do relatório | `512` |

`CONTEXT_WINDOW=5` → agente recebe as últimas 5 perguntas + 5 respostas do histórico.  
`CONTEXT_WINDOW=0` → agente stateless (sem memória de turnos anteriores).  
`TOP_P` disponível para todos os agentes via `<AGENTE>_TOP_P` (padrão `1.0`).

### Exemplo: usar GPT-4o no KnowledgeAgent

```env
KNOWLEDGE_PROVIDER=openai
KNOWLEDGE_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

Todos os outros agentes continuam no Groq. Não é necessário alterar nenhum código.

---

## Modelos usados

| Agente | Provider padrão | Modelo padrão | Justificativa |
|---|---|---|---|
| Guard | Groq | `llama-3.1-8b-instant` | Leve e rápido — roda antes de tudo |
| Router | Groq | `llama-3.1-8b-instant` | Classificação simples não exige modelo grande |
| Knowledge | Groq | `llama-3.3-70b-versatile` | Raciocínio robusto para interpretar documentos |
| Data | Groq | `llama-3.3-70b-versatile` | Geração de SQL + aplicação de regras de negócio |
| Escalation | Groq | `llama-3.3-70b-versatile` | Avaliação de regras complexas do playbook |

Provider e modelo são substituíveis por agente via `.env` sem alterar código.  
Para usar OpenAI, adicione `OPENAI_API_KEY` no `.env` e instale: `pip install langchain-openai`.

---

## Decisões técnicas e trade-offs

### Chain direta em vez de AgentExecutor (Knowledge e Data)
Os agentes Knowledge e Data foram simplificados para chains diretas (`prompt | llm | StrOutputParser()`), eliminando dependência de `AgentExecutor` e funções como `create_react_agent` / `create_tool_calling_agent` que apresentaram incompatibilidades com versões recentes do LangChain. O KnowledgeAgent carrega todos os documentos no prompt; o DataAgent usa dois passos explícitos (gera SQL → executa → interpreta).

### Multi-provider: Groq e OpenAI
Cada agente tem um `<AGENTE>_PROVIDER` no `.env` (`groq` ou `openai`). A factory `build_llm()` em `core/config.py` instancia o cliente correto — os agentes não sabem qual provider estão usando. Groq é o padrão: inferência rápida e tier gratuito de desenvolvimento. OpenAI pode ser usado em agentes que exigem maior capacidade de raciocínio. Trade-off do Groq: limites de rate mais apertados em uso intenso.

### Janela de contexto por fatiamento de lista
Histórico centralizado no Orchestrator; cada agente fatia os últimos N turnos e converte para `HumanMessage`/`AIMessage` antes de invocar. Controle independente por agente via `.env`.

### SQLite local
Zero infraestrutura adicional. Para produção, basta trocar a connection string em `core/database.py` — todo o restante do código é agnóstico ao banco.

### Sessões em memória
Simples e sem dependências externas. Histórico perdido ao reiniciar o servidor. Pontos de substituição por Redis marcados como TODO no `api.py`.

### Escalonamento silencioso
O usuário recebe mensagem neutra; o relatório completo (nível, evidência, próximos passos) é salvo apenas no banco. Evita expor informações internas e mantém rastreabilidade para o time de operações.

### Parsing por regex com fallbacks
Instrução de formato no system prompt + extração por regex. Fallbacks garantem que situações críticas (fraud_review, chargeback) nunca sejam ignoradas silenciosamente mesmo quando o modelo diverge do formato instruído.

---

## Rate Limit

Quando o Groq retorna erro 429 (Too Many Requests), o Orchestrator captura via `core/rate_limit.py` e exibe ao usuário:

> *"O assistente está temporariamente sobrecarregado (limite de requisições atingido). Aguarde alguns instantes e tente novamente."*

Nenhum erro HTTP 500 é propagado. O turno é registrado no histórico da sessão com `agent_selected: "rate_limit"` para rastreabilidade.

---

## Clock Tool

Os agentes Knowledge e Data injetam a data atual de Brasília no prompt via `tools/clock_tool.py`:

```python
from tools.clock_tool import hoje_brasilia
data_hoje = hoje_brasilia()   # "22/06/2026"
```

Isso permite que o LLM calcule diferenças de dias corretamente sem alucinar a data, ex:

> *"O reembolso foi aprovado há 10 dias (desde 12/06/2026). O prazo de 7 dias venceu em 19/06/2026."*

A chamada é rastreada pelo LangSmith como `run_type="tool"` (aparece no trace como `clock_tool`).

---

## Rastreamento de Tools (ToolCall)

Cada chamada de ferramenta feita pelos agentes (`clock_tool`, `sql_query`) gera um `ToolCall` definido em `core/trace.py`. O Orchestrator anexa esses registros ao histórico da sessão com `role="tool"`, tornando-os visíveis em `GET /session/{id}/history`:

```json
{
  "role":   "tool",
  "agent":  "data_agent",
  "tool":   "sql_query",
  "input":  { "sql": "SELECT * FROM pedidos WHERE id = 'P1008'" },
  "output": "[('P1008', 'entregue', '2026-06-12')]"
}
```

Os registros de tool **não poluem o contexto enviado ao LLM** — o `_truncar_historico` filtra apenas `user` e `assistant`.

---

## Limitações conhecidas

- Sessões não sobrevivem ao restart do servidor (armazenamento em memória)
- Sem autenticação nos endpoints (marcado como TODO em `api.py`)
- `top_p` passado via `model_kwargs` — sem validação tipada pelo LangChain
- Parsing baseado em regex pode falhar em respostas muito fora do formato instruído
- DataAgent usa duas chamadas de LLM por mensagem (geração de SQL + interpretação) — latência maior que os demais agentes
