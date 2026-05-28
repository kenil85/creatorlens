"""
Transcription Service
─────────────────────
1. Downloads audio via yt-dlp (no full video, audio-only)
2. Sends to OpenAI Whisper API for transcription with word timestamps
3. Performs naive speaker diarization by pause detection
"""

import asyncio
import os
import time
import tempfile
from pathlib import Path
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import TranscriptSegment

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

COST_PER_MINUTE_WHISPER = 0.006  # $0.006 per minute


async def download_audio(video_url: str, output_dir: str) -> tuple[str, dict]:
    """Download audio-only using yt-dlp. Returns (file_path, metadata)."""
    output_path = os.path.join(output_dir, "audio.%(ext)s")

    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "5",          # Medium quality — enough for speech
        "--max-filesize", "50m",         # Safety limit
        "--no-playlist",
        "--write-info-json",
        "--quiet",
        "-o", output_path,
        video_url,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {stderr.decode()[:500]}")

    # Find downloaded file
    audio_file = next(Path(output_dir).glob("audio.mp3"), None)
    if not audio_file:
        raise RuntimeError("Audio file not found after download")

    # Read metadata
    import json
    meta_file = next(Path(output_dir).glob("*.info.json"), None)
    metadata = {}
    if meta_file:
        metadata = json.loads(meta_file.read_text())

    return str(audio_file), {
        "title": metadata.get("title", "Unknown"),
        "duration": metadata.get("duration", 0),
        "uploader": metadata.get("uploader", "Unknown"),
        "view_count": metadata.get("view_count", 0),
    }


async def transcribe_audio(audio_path: str) -> dict:
    """
    Send audio to Whisper API.
    Returns raw Whisper response with word-level timestamps.
    """
    t0 = time.monotonic()

    with open(audio_path, "rb") as f:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
        )

    latency_ms = (time.monotonic() - t0) * 1000
    logger.info("whisper.transcribed", latency_ms=round(latency_ms))

    return {
        "text": response.text,
        "segments": response.segments or [],
        "words": response.words or [],
        "duration": response.duration or 0,
        "latency_ms": latency_ms,
    }


def diarize_speakers(segments: list) -> list[TranscriptSegment]:
    """
    Naive speaker diarization based on pause gaps.
    - Pauses > 1.5s → likely speaker change
    - Alternates between SPK_0 and SPK_1
    This is a heuristic; production would use pyannote.audio.
    """
    diarized = []
    current_speaker = 0

    for i, seg in enumerate(segments):
        # Detect pause gap from previous segment
        if i > 0:
            gap = seg.get("start", 0) - segments[i - 1].get("end", 0)
            if gap > 1.5:
                current_speaker = 1 - current_speaker  # toggle speaker

        diarized.append(TranscriptSegment(
            speaker=f"SPK_{current_speaker}",
            start=round(seg.get("start", 0), 2),
            end=round(seg.get("end", 0), 2),
            text=seg.get("text", "").strip(),
        ))

    return diarized


def calculate_whisper_cost(duration_seconds: float) -> float:
    minutes = duration_seconds / 60
    return round(minutes * COST_PER_MINUTE_WHISPER, 6)


async def process_video(video_url: str) -> tuple[list[TranscriptSegment], dict, float]:
    """
    Full ingestion pipeline.
    Returns (segments, video_meta, cost_usd)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("ingestion.start", url=video_url)

        audio_path, meta = await download_audio(video_url, tmpdir)
        logger.info("ingestion.downloaded", title=meta.get("title"))

        result = await transcribe_audio(audio_path)
        segments = diarize_speakers(result["segments"])

        cost = calculate_whisper_cost(result["duration"])
        meta["whisper_cost"] = cost
        meta["duration"] = result["duration"]

        logger.info("ingestion.complete",
                    segments=len(segments),
                    duration=result["duration"],
                    cost_usd=cost)

        return segments, meta, cost
