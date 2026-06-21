"""
Utilitário compartilhado para manipulação de histórico de chat.

Usado por todos os agentes que recebem contexto de conversas anteriores.
"""


def truncar_historico(chat_history: list[dict], context_window: int) -> list[dict]:
    """
    Retorna apenas as últimas `context_window` trocas do histórico.
    Cada troca = 2 mensagens (user + assistant).
    context_window=0 → retorna lista vazia (agente sem memória).
    """
    if context_window == 0:
        return []
    return chat_history[-(context_window * 2):]


def formatar_historico_texto(chat_history: list[dict]) -> str:
    """
    Formata histórico como texto simples para inclusão em prompts.
    Retorna "Nenhum" se a lista estiver vazia.
    """
    if not chat_history:
        return "Nenhum"
    return "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in chat_history
    )
