"""
Fábrica compartilhada para criação de agentes ReAct com AgentExecutor.

Usado pelo KnowledgeAgent e DataAgent que seguem o mesmo padrão:
    1. Criar LLM via ChatGroq
    2. Montar prompt com system + chat_history + input + agent_scratchpad
    3. Criar react agent e envolver em AgentExecutor
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_react_agent, AgentExecutor

from core.llm_factory import create_llm


def create_react_executor(
    params: dict,
    system_prompt: str,
    tools: list,
    verbose: bool = True,
    max_iterations: int | None = None,
) -> AgentExecutor:
    """
    Cria um AgentExecutor ReAct configurado com os parâmetros fornecidos.

    Args:
        params: dicionário de parâmetros do agente (model, temperature, max_tokens)
        system_prompt: prompt de sistema já formatado (com variáveis resolvidas)
        tools: lista de tools LangChain disponíveis para o agente
        verbose: ativar logs detalhados do AgentExecutor
        max_iterations: limite de iterações do ReAct (None = sem limite)

    Returns:
        AgentExecutor pronto para .invoke()
    """
    llm = create_llm(params)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_react_agent(llm, tools, prompt)

    executor_kwargs: dict = {
        "agent": agent,
        "tools": tools,
        "verbose": verbose,
        "handle_parsing_errors": True,
    }
    if max_iterations is not None:
        executor_kwargs["max_iterations"] = max_iterations

    return AgentExecutor(**executor_kwargs)
