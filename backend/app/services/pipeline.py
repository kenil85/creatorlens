"""
Pipeline Orchestrator
──────────────────────
Orchestrates all services and streams progress via Server-Sent Events (SSE).
Each pipeline stage emits events the frontend consumes in real-time.
"""

import asyncio
import json
import time
import uuid
from typing import AsyncGenerator
from app.core.logging import logger
from app.models.schemas import PipelineResult, PipelineStatus, PipelineEvent, OfferArchitecture
from app.services.transcription import process_video
from app.services.agents import run_agents
from app.services.vectorstore import embed_transcript
from app.services.repurpose import generate_content_map

# In-memory job store (use Redis in production)
_jobs: dict[str, PipelineResult] = {}


def get_job(job_id: str) -> PipelineResult | None:
    return _jobs.get(job_id)


def _event(event: str, data: dict = None, message: str = None, progress: float = None, stage: str = None) -> str:
    """Format a Server-Sent Event string."""
    payload = PipelineEvent(
        event=event,
        stage=stage,
        data=data,
        message=message,
        progress=progress,
    )
    return f"data: {payload.model_dump_json()}\n\n"


async def run_pipeline_stream(video_url: str) -> AsyncGenerator[str, None]:
    """
    Full pipeline as an async generator yielding SSE strings.
    Frontend connects to this via EventSource.
    """
    job_id = str(uuid.uuid4())[:8]
    start_time = time.monotonic()

    result = PipelineResult(
        job_id=job_id,
        status=PipelineStatus.QUEUED,
        video_url=video_url,
    )
    _jobs[job_id] = result

    yield _event("job_created", data={"job_id": job_id}, message=f"Job {job_id} created")

    try:
        # ── STAGE 1: Ingestion + Transcription ─────────────────────────────────
        yield _event("stage_start", stage="ingestion", progress=0,
                     message="Fetching video and transcribing audio...")
        result.status = PipelineStatus.INGESTING

        segments, meta, whisper_cost = await process_video(video_url)

        result.transcript = segments
        result.video_title = meta.get("title", "Unknown")
        result.duration_seconds = meta.get("duration", 0)
        result.total_cost_usd += whisper_cost

        yield _event("stage_done", stage="ingestion", progress=20, data={
            "segments": len(segments),
            "title": result.video_title,
            "duration": result.duration_seconds,
            "cost_usd": whisper_cost,
            "transcript": [s.model_dump() for s in segments[:10]],  # First 10 for preview
        }, message=f"Transcribed {len(segments)} segments from '{result.video_title}'")

        # ── STAGE 2: LangGraph Agents ───────────────────────────────────────────
        yield _event("stage_start", stage="agents", progress=20,
                     message="Running LangGraph multi-agent analysis...")
        result.status = PipelineStatus.ANALYZING

        # Stream agent-by-agent updates
        agent_names = ["TopicModeler", "SentimentAnalyzer", "MonetizationDetector", "OfferArchitect"]
        for i, name in enumerate(agent_names):
            yield _event("agent_update", stage="agents",
                         progress=20 + (i * 10),
                         data={"agent": name, "status": "firing"},
                         message=f"Agent {i+1}/4: {name} running...")
            await asyncio.sleep(0.1)  # Allow SSE flush

        agent_results, offer_data, agent_tokens, agent_cost = await run_agents(
            segments, result.video_title or "Creator Video"
        )

        result.agent_results = agent_results
        result.total_tokens += agent_tokens
        result.total_cost_usd += agent_cost

        # Parse offer
        try:
            result.offer = OfferArchitecture(
                title=offer_data.get("title", "Untitled"),
                price_anchor=offer_data.get("price_anchor", "$2,997"),
                core_promise=offer_data.get("core_promise", ""),
                hook=offer_data.get("hook", ""),
                modules=offer_data.get("modules", []),
                pain_points=offer_data.get("pain_points", []),
                transformation=offer_data.get("transformation", ""),
            )
        except Exception as e:
            logger.warning("offer.parse_failed", error=str(e))

        yield _event("stage_done", stage="agents", progress=60, data={
            "agents_completed": len(agent_results),
            "tokens": agent_tokens,
            "cost_usd": agent_cost,
            "offer_title": offer_data.get("title", ""),
            "agent_results": [r.model_dump() for r in agent_results],
        }, message=f"All 4 agents complete — {agent_tokens} tokens used")

        # ── STAGE 3: Vector Embedding ───────────────────────────────────────────
        yield _event("stage_start", stage="embedding", progress=60,
                     message="Chunking and embedding transcript into pgvector...")
        result.status = PipelineStatus.EMBEDDING

        chunks, embed_tokens, embed_cost = await embed_transcript(job_id, segments)

        result.chunks = chunks
        result.total_tokens += embed_tokens
        result.total_cost_usd += embed_cost

        yield _event("stage_done", stage="embedding", progress=80, data={
            "chunks": len(chunks),
            "tokens": embed_tokens,
            "cost_usd": embed_cost,
            "chunks_preview": [c.model_dump() for c in chunks[:8]],
        }, message=f"{len(chunks)} chunks embedded and stored in pgvector")

        # ── STAGE 4: Content Repurposing ────────────────────────────────────────
        yield _event("stage_start", stage="repurpose", progress=80,
                     message="Generating content repurposing map...")

        content_map, rep_tokens, rep_cost = await generate_content_map(
            segments, offer_data, result.video_title or "Creator Video"
        )

        result.content_map = content_map
        result.total_tokens += rep_tokens
        result.total_cost_usd += rep_cost

        yield _event("stage_done", stage="repurpose", progress=95, data={
            "content_map": content_map.model_dump(),
        }, message="Content map generated")

        # ── COMPLETE ────────────────────────────────────────────────────────────
        total_latency = (time.monotonic() - start_time) * 1000
        result.total_latency_ms = round(total_latency)
        result.status = PipelineStatus.COMPLETE

        # Calculate monetization score from agent output
        try:
            import json as _json
            for ar in agent_results:
                if ar.agent_name == "MonetizationDetector":
                    raw = ar.output.strip().lstrip("```json").rstrip("```").strip()
                    mono_data = _json.loads(raw)
                    result.monetization_score = mono_data.get("monetization_score", 0.0)
                    break
        except Exception:
            result.monetization_score = 0.75  # Default

        _jobs[job_id] = result

        yield _event("complete", progress=100, data={
            "job_id": job_id,
            "total_tokens": result.total_tokens,
            "total_cost_usd": round(result.total_cost_usd, 6),
            "total_latency_ms": result.total_latency_ms,
            "monetization_score": result.monetization_score,
            "result": result.model_dump(),
        }, message=f"Pipeline complete — ${result.total_cost_usd:.4f} total cost")

    except Exception as e:
        logger.error("pipeline.error", error=str(e), job_id=job_id)
        result.status = PipelineStatus.ERROR
        result.error = str(e)
        _jobs[job_id] = result
        yield _event("error", data={"error": str(e), "job_id": job_id},
                     message=f"Pipeline failed: {str(e)[:200]}")
