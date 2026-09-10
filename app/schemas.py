"""
Modelos Pydantic (parsing do corpo da requisição) + as mesmas
validações de negócio do server.js original, incluindo as mensagens
de erro em português — o frontend depende do texto exato de
`data.error`, então elas foram mantidas palavra por palavra.
"""
import re
from typing import Optional

from pydantic import BaseModel

from .youtube import parse_youtube_link

_HTTP_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


class LoginIn(BaseModel):
    password: Optional[str] = None


class MessageIn(BaseModel):
    title: Optional[str] = ""
    content: Optional[str] = ""
    author: Optional[str] = ""
    spirit: Optional[str] = ""
    image_url: Optional[str] = ""


class VideoIn(BaseModel):
    title: Optional[str] = ""
    youtube_url: Optional[str] = ""
    description: Optional[str] = ""


def validate_message(body: MessageIn) -> tuple[list[str], dict]:
    errors: list[str] = []
    title = (body.title or "").strip()
    content = (body.content or "").strip()
    author = (body.author or "").strip()
    spirit = (body.spirit or "").strip()
    image_url = (body.image_url or "").strip()

    if not title:
        errors.append("O título é obrigatório.")
    if len(title) > 120:
        errors.append("O título deve ter até 120 caracteres.")
    if not content:
        errors.append("A mensagem é obrigatória.")
    if len(content) > 4000:
        errors.append("A mensagem deve ter até 4000 caracteres.")
    if len(author) > 60:
        errors.append("O nome do autor deve ter até 60 caracteres.")
    if len(spirit) > 60:
        errors.append("O nome do mentor espiritual deve ter até 60 caracteres.")
    if len(image_url) > 1000:
        errors.append("A URL da imagem é muito longa.")
    if image_url and not _HTTP_URL_PATTERN.match(image_url):
        errors.append("A URL da imagem deve começar com http:// ou https://.")

    return errors, {
        "title": title,
        "content": content,
        "author": author,
        "spirit": spirit,
        "image_url": image_url,
    }


def validate_video(body: VideoIn) -> tuple[list[str], dict]:
    errors: list[str] = []
    title = (body.title or "").strip()
    youtube_url = (body.youtube_url or "").strip()
    description = (body.description or "").strip()

    if not title:
        errors.append("O título é obrigatório.")
    if len(title) > 120:
        errors.append("O título deve ter até 120 caracteres.")
    if not youtube_url:
        errors.append("O link do YouTube é obrigatório.")
    if len(description) > 500:
        errors.append("A descrição deve ter até 500 caracteres.")

    parsed = None
    if youtube_url:
        parsed = parse_youtube_link(youtube_url)
        if not parsed:
            errors.append(
                "Não foi possível reconhecer esse link como um vídeo ou "
                "playlist do YouTube."
            )

    return errors, {
        "title": title,
        "youtube_url": youtube_url,
        "description": description,
        "type": (parsed or {}).get("type", "video"),
        "video_id": (parsed or {}).get("video_id"),
        "playlist_id": (parsed or {}).get("playlist_id"),
    }
