"""
Login do mantenedor — limitado a 5 tentativas a cada 10 minutos por IP.

Observação: em ambiente serverless, o estado desse limitador vive em
memória de cada instância da função, então o limite é "best effort"
(uma nova instância fria reseta a contagem) — a mesma ressalva do
comentário original em server.js. Para um limite garantido entre
instâncias, use um contador externo (ex.: Upstash Redis).
"""
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import get_maintainer_password_hash
from ..schemas import LoginIn
from ..security import create_token, verify_password

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
@limiter.limit("5 per 10 minute")
async def login(request: Request, payload: LoginIn):
    password = payload.password

    if not password:
        raise HTTPException(status_code=400, detail="Informe a senha.")

    password_hash = get_maintainer_password_hash()
    if not verify_password(password, password_hash):
        raise HTTPException(status_code=401, detail="Senha incorreta.")

    return {"token": create_token()}
