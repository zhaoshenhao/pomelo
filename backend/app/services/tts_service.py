import logging

import edge_tts
from mutagen.mp3 import MP3

from app.config import settings

logger = logging.getLogger(__name__)


async def synthesize(text: str, voice: str, out_path: str) -> float:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)
    audio = MP3(out_path)
    return audio.info.length


def estimate_duration(text: str) -> float:
    if not text.strip():
        return 2.0
    return max(2.0, len(text) / settings.TTS_FALLBACK_CHARS_PER_SEC)
