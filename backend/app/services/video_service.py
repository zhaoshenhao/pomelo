import logging
import os
import re
import subprocess

logger = logging.getLogger(__name__)


def probe_duration(file_path: str) -> int:
    """Probe video duration in seconds using imageio-ffmpeg."""
    try:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError("imageio-ffmpeg not installed; cannot probe video duration")
    except Exception:
        raise RuntimeError("Failed to locate ffmpeg binary from imageio-ffmpeg")

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Video file not found: {file_path}")

    cmd = [ffmpeg, "-i", file_path, "-f", "null", "-"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        stderr = result.stderr
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timeout probing %s", file_path)
        return 0

    match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2})\.(\d+)", stderr)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        secs = int(match.group(3))
        total_seconds = hours * 3600 + minutes * 60 + secs
        return total_seconds

    logger.warning("Could not parse duration from ffmpeg output for %s", file_path)
    return 0
