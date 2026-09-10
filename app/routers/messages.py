"""
Rotas de mensagens do mural. Leitura pública, escrita restrita ao
mantenedor (Depends(require_auth)) — mesma regra do server.js.
"""
from fastapi import APIRouter, Depends, HTTPException, Response

from ..db import ensure_schema, get_pool
from ..schemas import MessageIn, validate_message
from ..security import require_auth

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("")
async def list_messages():
    await ensure_schema()
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM messages ORDER BY created_at DESC")
    return [dict(row) for row in rows]


@router.post("", status_code=201)
async def create_message(body: MessageIn, auth: dict = Depends(require_auth)):
    errors, data = validate_message(body)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))

    await ensure_schema()
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO messages (title, content, author, spirit, image_url)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        data["title"],
        data["content"],
        data["author"],
        data["spirit"],
        data["image_url"] or None,
    )
    return dict(row)


@router.put("/{message_id}")
async def update_message(
    message_id: int, body: MessageIn, auth: dict = Depends(require_auth)
):
    await ensure_schema()
    pool = await get_pool()

    existing = await pool.fetchrow("SELECT * FROM messages WHERE id = $1", message_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

    errors, data = validate_message(body)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))

    row = await pool.fetchrow(
        """
        UPDATE messages
        SET title = $1, content = $2, author = $3, spirit = $4, image_url = $5
        WHERE id = $6
        RETURNING *
        """,
        data["title"],
        data["content"],
        data["author"],
        data["spirit"],
        data["image_url"] or None,
        message_id,
    )
    return dict(row)


@router.delete("/{message_id}", status_code=204)
async def delete_message(message_id: int, auth: dict = Depends(require_auth)):
    await ensure_schema()
    pool = await get_pool()

    existing = await pool.fetchrow("SELECT * FROM messages WHERE id = $1", message_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

    await pool.execute("DELETE FROM messages WHERE id = $1", message_id)
    return Response(status_code=204)
