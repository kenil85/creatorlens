"""
Transcription Service — Groq Whisper (FREE)
────────────────────────────────────────────
1. Downloads audio via yt-dlp (audio-only)
2. Sends to Groq Whisper API — completely free
3. Speaker diarization by pause detection
"""

import asyncio
import os
import time
import tempfile
from pathlib import Path
from groq import AsyncGroq
from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import TranscriptSegment

settings = get_settings()
groq_client = AsyncGroq(api_key=settings.groq_api_key)


async def download_audio(video_url: str, output_dir: str) -> tuple[str, dict]:
    """Download audio-only using yt-dlp — Windows compatible."""
    import subprocess
    import shutil
    output_path = os.path.join(output_dir, "audio.%(ext)s")

    # Find ffmpeg path explicitly
    ffmpeg_path = r"D:\Master\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"

    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "5",
        "--max-filesize", "25m",
        "--no-playlist",
        "--write-info-json",
        "--ffmpeg-location", ffmpeg_path,
        "-o", output_path,
        video_url,
    ]

    # Pass current PATH to subprocess so it finds all tools
    import os as _os
    env = _os.environ.copy()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    )

    # Only fail on actual ERROR, not warnings
    if result.returncode != 0 and "ERROR:" in result.stderr:
        raise RuntimeError(f"yt-dlp failed: {result.stderr[:500]}")

    audio_file = next(Path(output_dir).glob("audio.mp3"), None)
    if not audio_file:
        raise RuntimeError(f"Audio file not found. yt-dlp output: {result.stderr[:300]}")

    import json
    meta_file = next(Path(output_dir).glob("*.info.json"), None)
    metadata = {}
    if meta_file:
        metadata = json.loads(meta_file.read_text())

    return str(audio_file), {
        "title": metadata.get("title", "Unknown"),
        "duration": metadata.get("duration", 0),
        "uploader": metadata.get("uploader", "Unknown"),
    }


async def transcribe_audio(audio_path: str) -> dict:
    """
    Transcribe via Groq Whisper — FREE, very fast.
    groq whisper-large-v3 is faster than OpenAI and free.
    """
    t0 = time.monotonic()

    with open(audio_path, "rb") as f:
        response = await groq_client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    latency_ms = (time.monotonic() - t0) * 1000
    logger.info("groq_whisper.transcribed", latency_ms=round(latency_ms))

    segments = response.segments or []
    # Groq returns segments as dicts or objects
    parsed = []
    for seg in segments:
        if isinstance(seg, dict):
            parsed.append(seg)
        else:
            parsed.append({
                "start": getattr(seg, "start", 0),
                "end": getattr(seg, "end", 0),
                "text": getattr(seg, "text", ""),
            })

    return {
        "text": response.text,
        "segments": parsed,
        "duration": getattr(response, "duration", 0) or 0,
        "latency_ms": latency_ms,
    }


def diarize_speakers(segments: list) -> list[TranscriptSegment]:
    """Naive speaker diarization based on pause gaps > 1.5s."""
    diarized = []
    current_speaker = 0

    for i, seg in enumerate(segments):
        if i > 0:
            gap = seg.get("start", 0) - segments[i - 1].get("end", 0)
            if gap > 1.5:
                current_speaker = 1 - current_speaker

        diarized.append(TranscriptSegment(
            speaker=f"SPK_{current_speaker}",
            start=round(seg.get("start", 0), 2),
            end=round(seg.get("end", 0), 2),
            text=seg.get("text", "").strip(),
        ))

    return diarized


async def process_video(video_url: str) -> tuple[list[TranscriptSegment], dict, float]:
    """Full ingestion pipeline. Returns (segments, meta, cost=0 because Groq is free)."""
    import traceback
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            logger.info("ingestion.start", url=video_url)
            audio_path, meta = await download_audio(video_url, tmpdir)
            logger.info("ingestion.downloaded", title=meta.get("title"))

            result = await transcribe_audio(audio_path)
            segments = diarize_speakers(result["segments"])

            meta["duration"] = result["duration"]
            meta["whisper_cost"] = 0.0

            logger.info("ingestion.complete",
                        segments=len(segments),
                        duration=result["duration"])

            return segments, meta, 0.0
    except Exception as e:
        logger.error("ingestion.failed", error=str(e), traceback=traceback.format_exc())
        raise