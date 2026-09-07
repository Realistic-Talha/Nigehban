"""Video frame extraction via ffmpeg."""

import asyncio
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

MAX_FRAMES = 10
MAX_DURATION_SEC = 30


async def extract_frames(video_path: str, max_frames: int = MAX_FRAMES) -> list[str]:
    """Extract JPEG frames from a local video file. Returns temp file paths."""
    out_dir = tempfile.mkdtemp(prefix="nigehban_frames_")
    pattern = os.path.join(out_dir, "frame_%03d.jpg")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-t",
        str(MAX_DURATION_SEC),
        "-vf",
        f"select='not(mod(n\\,{max(1, MAX_DURATION_SEC)})')',scale=640:-1",
        "-frames:v",
        str(max_frames),
        pattern,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    frames = sorted(
        [os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.endswith(".jpg")]
    )
    return frames[:max_frames]
