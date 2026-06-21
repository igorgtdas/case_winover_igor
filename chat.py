"""
Interface CLI do AtlasShop Assist.
Uso: python chat.py
"""

import logging

from orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 60)
    print("  AtlasShop Assist — Suporte Interno")
    print("  Digite 'sair' ou 'exit' para encerrar")
    print("=" * 60)

    orchestrator = Orchestrator()

    while True:
        try:
            user_input = input("\nVocê: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando...")
            break

        if user_input.lower() in {"sair", "exit", "quit"}:
            print("Encerrando...")
            break

        if not user_input:
            continue

        try:
            response = orchestrator.chat(user_input)
        except RuntimeError as exc:
            logger.error("Erro ao processar mensagem: %s", exc)
            print(f"\nAssistente: [ERRO] Não foi possível processar sua mensagem. Tente novamente.")
            continue

        print(f"\nAssistente: {response}")


if __name__ == "__main__":
    main()
