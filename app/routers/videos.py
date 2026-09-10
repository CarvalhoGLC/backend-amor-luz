"""
Rotas de vídeos do YouTube indicados pelo mantenedor — mesma regra
das mensagens: leitura pública, escrita restrita.
"""
from fastapi import APIRouter, Depends, HTTPException, Response

from ..db import ensure_schema, get_pool
from ..schemas import VideoIn, validate_video
from ..security import require_auth

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("")
async def list_videos():
    await ensure_schema()
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM videos ORDER BY created_at DESC")
    return [dict(row) for row in rows]


@router.post("", status_code=201)
async def create_video(body: VideoIn, auth: dict = Depends(require_auth)):
    errors, data = validate_video(body)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))

    await ensure_schema()
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO videos (title, video_id, youtube_url, description, type, playlist_id)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        data["title"],
        data["video_id"],
        data["youtube_url"],
        data["description"],
        data["type"],
        data["playlist_id"],
    )
    return dict(row)


@router.delete("/{video_id}", status_code=204)
async def delete_video(video_id: int, auth: dict = Depends(require_auth)):
    await ensure_schema()
    pool = await get_pool()

    existing = await pool.fetchrow("SELECT * FROM videos WHERE id = $1", video_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")

    await pool.execute("DELETE FROM videos WHERE id = $1", video_id)
    return Response(status_code=204)
