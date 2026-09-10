"""
Acesso ao Postgres via asyncpg.

Em ambiente serverless não há disco persistente, então o banco de
dados vive em um Postgres hospedado (Vercel Postgres/Neon, Supabase,
etc.). A criação da tabela e das colunas é idempotente (IF NOT
EXISTS), o que permite evoluir o schema (como adicionar image_url)
sem um passo de migração separado — o próprio código garante o
estado mais atual.

O pool de conexões e a flag de "schema pronto" ficam em variáveis de
módulo, reaproveitadas entre invocações de uma mesma instância quente
da função — o equivalente Python ao `let schemaReady = null` do
db.js original.
"""
import asyncio
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import asyncpg

from .config import get_database_url

_pool: asyncpg.Pool | None = None
_schema_ready = False
_schema_lock = asyncio.Lock()


def _prepare_dsn(url: str) -> tuple[str, bool | str]:
    """Remove sslmode da query string (asyncpg trata SSL à parte) e devolve
    o DSN limpo junto com o valor a passar em ssl=..."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    sslmode = (query.pop("sslmode", ["require"]) or ["require"])[0]
    dsn = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
    ssl: bool | str = False if sslmode == "disable" else "require"
    return dsn, ssl


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        url = get_database_url()
        if not url:
            raise RuntimeError(
                "Defina POSTGRES_URL (ou DATABASE_URL) nas variáveis de "
                "ambiente do projeto."
            )
        dsn, ssl = _prepare_dsn(url)
        _pool = await asyncpg.create_pool(dsn=dsn, ssl=ssl, min_size=0, max_size=5)
    return _pool


async def ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    async with _schema_lock:
        if _schema_ready:
            return
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id          SERIAL PRIMARY KEY,
                    title       TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    author      TEXT,
                    spirit      TEXT,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
            # Adicionado depois da versão original — coluna opcional para a
            # URL da imagem exibida no topo do card da mensagem.
            await conn.execute(
                "ALTER TABLE messages ADD COLUMN IF NOT EXISTS image_url TEXT;"
            )

            # Seção de vídeos do YouTube indicados pelo mantenedor.
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    id          SERIAL PRIMARY KEY,
                    title       TEXT NOT NULL,
                    video_id    TEXT NOT NULL,
                    youtube_url TEXT NOT NULL,
                    description TEXT,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )

            # Adicionado depois da versão original — suporte a playlists
            # inteiras, além de vídeos avulsos. "type" diz como montar o
            # embed: 'video' usa video_id, 'playlist' usa playlist_id.
            # video_id deixa de ser obrigatório porque uma playlist não tem
            # um vídeo único associado.
            await conn.execute(
                "ALTER TABLE videos ADD COLUMN IF NOT EXISTS type TEXT NOT NULL DEFAULT 'video';"
            )
            await conn.execute(
                "ALTER TABLE videos ADD COLUMN IF NOT EXISTS playlist_id TEXT;"
            )
            await conn.execute(
                "ALTER TABLE videos ALTER COLUMN video_id DROP NOT NULL;"
            )
        _schema_ready = True


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
