
import edge_tts
from mutagen.mp3 import MP3



async def synthesize(text: str, voice: str, out_path: str) -> float:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)
    audio = MP3(out_path)
    return audio.info.length
