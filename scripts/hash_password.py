"""
Gera o hash bcrypt de uma senha para colocar em MAINTAINER_PASSWORD_HASH
no .env

Uso:
    python scripts/hash_password.py "minha-senha-secreta"
"""
import sys

import bcrypt


def main() -> None:
    if len(sys.argv) < 2:
        print('Uso: python scripts/hash_password.py "sua-senha"', file=sys.stderr)
        sys.exit(1)

    password = sys.argv[1]
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    print("\nAdicione esta linha ao seu arquivo .env:\n")
    print(f"MAINTAINER_PASSWORD_HASH={hashed}\n")


if __name__ == "__main__":
    main()
