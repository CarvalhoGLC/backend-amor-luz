"""
Autenticação: senha do mantenedor (bcrypt) + token de sessão (JWT).

Mesma estratégia do backend em Node — uma única senha de mantenedor,
sem contas de usuário — só que com PyJWT e bcrypt no lugar de
jsonwebtoken e bcryptjs.
"""
import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Header, HTTPException

from .config import get_jwt_secret, get_maintainer_password_hash, get_token_expires_in

_EXPIRES_IN_PATTERN = re.compile(r"^(\d+)([smhd])$")
_UNIT_TO_KWARG = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


def _parse_expires_in(value: str) -> timedelta:
    """Entende os mesmos formatos simples que jsonwebtoken aceita para
    expiresIn: um número em segundos, ou um número seguido de s/m/h/d."""
    value = (value or "").strip()
    match = _EXPIRES_IN_PATTERN.match(value)
    if match:
        amount, unit = match.groups()
        return timedelta(**{_UNIT_TO_KWARG[unit]: int(amount)})
    if value.isdigit():
        return timedelta(seconds=int(value))
    return timedelta(hours=12)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Hash malformado nas variáveis de ambiente — trata como senha inválida
        # em vez de propagar um 500 pouco claro.
        return False


def create_token() -> str:
    secret = get_jwt_secret()
    now = datetime.now(tz=timezone.utc)
    payload = {
        "role": "maintainer",
        "iat": now,
        "exp": now + _parse_expires_in(get_token_expires_in()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


async def require_auth(authorization: str | None = Header(default=None)) -> dict:
    """Dependência equivalente ao middleware requireAuth do Express —
    aplique com Depends(require_auth) em qualquer rota protegida."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Token ausente.")

    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
