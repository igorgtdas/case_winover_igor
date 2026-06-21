"""
Interface CLI do AtlasShop Assist.
Uso: python chat.py
"""

from orchestrator import Orchestrator


def main():
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

        response = orchestrator.chat(user_input)
        print(f"\nAssistente: {response}")


if __name__ == "__main__":
    main()
