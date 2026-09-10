"""
Dependência compartilhada que garante a presença das variáveis de
ambiente obrigatórias antes de atender qualquer rota — o equivalente
Python ao middleware que rodava antes de tudo no server.js original.
"""
import logging

from .config import has_required_auth_config

logger = logging.getLogger("orvalho")


class ConfigError(Exception):
    """As variáveis de ambiente obrigatórias (JWT_SECRET,
    MAINTAINER_PASSWORD_HASH) não estão definidas."""


def require_config() -> None:
    if not has_required_auth_config():
        logger.error(
            "Configuração ausente: defina JWT_SECRET e MAINTAINER_PASSWORD_HASH "
            "nas variáveis de ambiente do projeto na Vercel."
        )
        raise ConfigError()
