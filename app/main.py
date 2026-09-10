"""
Ponto de entrada FastAPI.

Na Vercel, este arquivo é detectado automaticamente (convenção
app/main.py) e servido como uma única Vercel Function — não há mais
um api/index.py separado nem rewrites no vercel.json, como havia no
backend em Express.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_cors_origins
from .db import close_pool
from .dependencies import ConfigError, require_config
from .routers import messages, videos
from .routers.auth import limiter
from .routers.auth import router as auth_router

logger = logging.getLogger("orvalho")

MAX_BODY_BYTES = 100 * 1024  # equivalente ao express.json({ limit: '100kb' })


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()


# dependencies=[...] no nível do app roda antes de QUALQUER rota — inclusive
# a raiz "/" — reproduzindo o middleware que o Express registrava com
# app.use(...) antes de todas as rotas.
app = FastAPI(title="Orvalho backend", lifespan=lifespan, dependencies=[Depends(require_config)])
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Cabeçalhos de segurança equivalentes ao helmet() do Express."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Strict-Transport-Security"] = "max-age=15552000; includeSubDomains"
    return response


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": "Corpo da requisição excede o limite permitido."},
        )
    return await call_next(request)


@app.exception_handler(ConfigError)
async def config_error_handler(request: Request, exc: ConfigError):
    return JSONResponse(
        status_code=500,
        content={"error": "Configuração do servidor incompleta. Verifique as variáveis de ambiente."},
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Muitas tentativas. Aguarde alguns minutos e tente novamente."},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # O frontend lê sempre `data.error` — reformata o padrão
    # {"detail": ...} do FastAPI/Starlette para {"error": ...}.
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "Dados inválidos na requisição."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro não tratado: %s", exc)
    return JSONResponse(status_code=500, content={"error": "Erro interno do servidor."})


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Orvalho backend",
        "endpoints": ["/api/messages", "/api/auth/login"],
    }


app.include_router(auth_router)
app.include_router(messages.router)
app.include_router(videos.router)
