"""Comandos de linha de comando.

  python -m app.cli init-db
  python -m app.cli create-admin --email voce@exemplo.com [--nome "Seu Nome"]
"""

from __future__ import annotations

import argparse
import getpass
import sys

from app.auth_service import audit
from app.db import SessionLocal, init_db
from app.models import Usuario
from app.security import hash_password


def create_admin(email: str, nome: str) -> int:
    init_db()
    email = email.strip().lower()
    with SessionLocal() as db:
        existing = db.query(Usuario).filter(Usuario.email == email).one_or_none()
        if existing:
            existing.papel, existing.ativo = "admin", True
            db.commit()
            print(f"Usuário {email} já existia: promovido a administrador.")
            return 0
        senha = getpass.getpass("Senha (mín. 8 caracteres): ")
        if len(senha) < 8 or senha != getpass.getpass("Repita a senha: "):
            print("Senha inválida ou diferente.", file=sys.stderr)
            return 1
        user = Usuario(nome=nome, email=email, senha_hash=hash_password(senha), papel="admin")
        db.add(user)
        db.commit()
        audit(db, "admin_criado", user=user, alvo=email, detalhe="criado via CLI")
        print(f"Administrador {email} criado.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="cria tabelas e colunas novas")
    p = sub.add_parser("create-admin", help="cria (ou promove) um administrador")
    p.add_argument("--email", required=True)
    p.add_argument("--nome", default="Administrador")
    args = parser.parse_args(argv)
    if args.cmd == "init-db":
        init_db()
        print("Banco inicializado.")
        return 0
    return create_admin(args.email, args.nome)


if __name__ == "__main__":
    raise SystemExit(main())
