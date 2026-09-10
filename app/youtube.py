"""
Reconhecimento de links do YouTube — porta direta das expressões
regulares usadas no server.js original.

Aceita os formatos mais comuns de link do YouTube e devolve só o ID
de 11 caracteres do vídeo, que é o que a API de embed realmente
precisa, além do ID de playlist quando presente.
"""
import re
from typing import Optional, TypedDict

_VIDEO_ID_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtube\.com/embed/|youtube\.com/v/|"
    r"youtube\.com/shorts/|youtube\.com/live/|youtu\.be/)([a-zA-Z0-9_-]{11})"
)
_PLAYLIST_ID_PATTERN = re.compile(r"[?&]list=([a-zA-Z0-9_-]+)")
_PLAYLIST_URL_PATTERN = re.compile(r"youtube\.com/playlist")


class ParsedYouTubeLink(TypedDict):
    type: str
    video_id: Optional[str]
    playlist_id: Optional[str]


def extract_youtube_id(url: str) -> Optional[str]:
    match = _VIDEO_ID_PATTERN.search(url)
    return match.group(1) if match else None


def extract_playlist_id(url: str) -> Optional[str]:
    # Cobre tanto links de playlist pura (youtube.com/playlist?list=...)
    # quanto links de um vídeo específico dentro de uma playlist
    # (?v=...&list=...).
    match = _PLAYLIST_ID_PATTERN.search(url)
    return match.group(1) if match else None


def parse_youtube_link(url: str) -> Optional[ParsedYouTubeLink]:
    """Decide, a partir do link colado, se é um vídeo avulso ou uma
    playlist inteira — sem precisar de um campo separado no formulário."""
    playlist_id = extract_playlist_id(url)
    video_id = extract_youtube_id(url)
    is_playlist_url = bool(_PLAYLIST_URL_PATTERN.search(url))

    if is_playlist_url and playlist_id:
        return {"type": "playlist", "video_id": None, "playlist_id": playlist_id}
    if video_id:
        return {"type": "video", "video_id": video_id, "playlist_id": None}
    if playlist_id:
        return {"type": "playlist", "video_id": None, "playlist_id": playlist_id}
    return None
