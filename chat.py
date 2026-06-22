"""
Cliente CLI do AtlasShop Assist.
Bate na API REST — o servidor deve estar rodando (docker compose up).

Uso:
    python chat.py
    python chat.py --url http://localhost:8000
"""

import argparse
import sys
import uuid
import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:8000"


def _post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def criar_sessao(base: str, nome: str, email: str) -> str:
    session_id = f"cli-{uuid.uuid4().hex[:8]}"
    _post(f"{base}/session/start", {
        "session_id": session_id,
        "user_name": nome,
        "user_email": email,
    })
    return session_id


def enviar_mensagem(base: str, session_id: str, message: str) -> str:
    resp = _post(f"{base}/chat", {"session_id": session_id, "message": message})
    return resp.get("response", "(sem resposta)")


def cabecalho():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║        AtlasShop Assist — Suporte Interno        ║")
    print("╚══════════════════════════════════════════════════╝")
    print()


def configurar_sessao() -> tuple[str, str]:
    print("Configure a sessão antes de começar:\n")
    nome  = input("  Seu nome       : ").strip() or "Colaborador"
    email = input("  Seu e-mail     : ").strip() or "colaborador@atlasshop.com"
    return nome, email


def main():
    parser = argparse.ArgumentParser(description="CLI do AtlasShop Assist")
    parser.add_argument("--url", default=BASE_URL, help="Base URL da API (padrão: http://localhost:8000)")
    args = parser.parse_args()
    base = args.url.rstrip("/")

    cabecalho()

    # Verifica se a API está no ar
    try:
        _get(f"{base}/health")
    except Exception:
        print(f"  Erro: não foi possível conectar em {base}")
        print("  Certifique-se de que o servidor está rodando:")
        print("    docker compose up\n")
        sys.exit(1)

    nome, email = configurar_sessao()

    try:
        session_id = criar_sessao(base, nome, email)
    except Exception as e:
        print(f"\n  Erro ao criar sessão: {e}\n")
        sys.exit(1)

    print(f"\n  Sessão iniciada. Olá, {nome}!")
    print(f"  Session ID : {session_id}")
    print(f"  Histórico  : GET http://localhost:8000/session/{session_id}/history")
    print("  Digite 'sair' para encerrar | 'historico' para ver o log\n")
    print("─" * 52)

    while True:
        try:
            msg = input(f"\n{nome}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Encerrando. Até logo!\n")
            break

        if not msg:
            continue

        if msg.lower() in {"sair", "exit", "quit"}:
            print("\n  Encerrando. Até logo!\n")
            break

        if msg.lower() == "historico":
            try:
                hist = _get(f"{base}/session/{session_id}/history")
                print()
                for entry in hist.get("messages", []):
                    role = entry.get("role", "?")
                    if role == "tool":
                        print(f"  [tool:{entry.get('tool')}] in={entry.get('input')} out={entry.get('output')}")
                    else:
                        print(f"  [{role}] {entry.get('content', '')[:120]}")
            except Exception as e:
                print(f"  Erro ao buscar histórico: {e}")
            continue

        try:
            resposta = enviar_mensagem(base, session_id, msg)
            print(f"\nAssistente: {resposta}")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"\n  Erro {e.code}: {body[:200]}")
        except Exception as e:
            print(f"\n  Erro: {e}")


if __name__ == "__main__":
    main()
