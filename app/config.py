"""
Configuração lida das variáveis de ambiente.

Espelha o backend em Node: mesmas variáveis (JWT_SECRET,
TOKEN_EXPIRES_IN, MAINTAINER_PASSWORD_HASH, CORS_ORIGIN), mais as
variáveis de conexão com o Postgres que a Vercel injeta quando um
banco Vercel Postgres/Neon está associado ao projeto.
"""
import os


def get_jwt_secret() -> str | None:
    return os.environ.get("JWT_SECRET")


def get_token_expires_in() -> str:
    return os.environ.get("TOKEN_EXPIRES_IN", "12h")


def get_maintainer_password_hash() -> str | None:
    return os.environ.get("MAINTAINER_PASSWORD_HASH")


def get_cors_origins() -> list[str]:
    origin = os.environ.get("CORS_ORIGIN")
    if not origin:
        return ["*"]
    return [o.strip() for o in origin.split(",") if o.strip()]


def get_database_url() -> str | None:
    # POSTGRES_URL é a variável que a integração Vercel Postgres / Neon
    # define automaticamente. DATABASE_URL cobre outros provedores
    # (Supabase, Railway, etc.) que usam o nome mais genérico.
    return (
        os.environ.get("POSTGRES_URL")
        or os.environ.get("POSTGRES_URL_NON_POOLING")
        or os.environ.get("DATABASE_URL")
    )


def has_required_auth_config() -> bool:
    return bool(get_jwt_secret() and get_maintainer_password_hash())
