"""
Vector Embedding + Semantic Search Service
───────────────────────────────────────────
1. Chunks transcript segments into overlapping windows
2. Embeds each chunk via OpenAI text-embedding-3-small
3. Stores in Supabase pgvector
4. Semantic search with cosine similarity
"""

import time
import uuid
import math
import json
from openai import AsyncOpenAI
from supabase import create_client, Client
from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import TranscriptSegment, VectorChunk, SearchResult

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536
COST_PER_TOKEN_EMBED = 0.00000002  # $0.02 per 1M tokens

# ── Supabase client ────────────────────────────────────────────────────────────
def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


# ── Chunking ───────────────────────────────────────────────────────────────────
def chunk_segments(
    segments: list[TranscriptSegment],
    chunk_size: int = 3,
    overlap: int = 1,
) -> list[dict]:
    """
    Sliding window chunking over transcript segments.
    chunk_size=3 means 3 segments per chunk, overlap=1 means 1 segment shared.
    """
    chunks = []
    step = chunk_size - overlap

    for i in range(0, len(segments), step):
        window = segments[i: i + chunk_size]
        if not window:
            break

        text = " ".join(seg.text for seg in window)
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "text": text,
            "start": window[0].start,
            "end": window[-1].end,
            "speaker": window[0].speaker,
            "segment_indices": list(range(i, min(i + chunk_size, len(segments)))),
        })

    return chunks


# ── Embedding ──────────────────────────────────────────────────────────────────
async def embed_texts(texts: list[str]) -> tuple[list[list[float]], int]:
    """
    Batch embed texts. Returns (embeddings, total_tokens).
    OpenAI supports up to 2048 inputs per request.
    """
    t0 = time.monotonic()
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
        encoding_format="float",
    )
    latency = (time.monotonic() - t0) * 1000
    tokens = response.usage.total_tokens

    logger.info("embed.done",
                count=len(texts),
                tokens=tokens,
                latency_ms=round(latency))

    return [item.embedding for item in response.data], tokens


# ── pgvector storage ───────────────────────────────────────────────────────────
async def store_chunks(
    job_id: str,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> None:
    """Store chunks + embeddings in Supabase pgvector table."""
    supabase = get_supabase()

    rows = []
    for chunk, emb in zip(chunks, embeddings):
        rows.append({
            "job_id": job_id,
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "start_time": chunk["start"],
            "end_time": chunk["end"],
            "speaker": chunk["speaker"],
            "embedding": emb,  # pgvector stores as array
        })

    # Upsert in batches of 50
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i: i + batch_size]
        supabase.table("video_chunks").upsert(batch).execute()
        logger.info("pgvector.stored", batch=i // batch_size + 1, count=len(batch))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Pure Python cosine similarity — no numpy needed."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Semantic search ────────────────────────────────────────────────────────────
async def semantic_search(
    job_id: str,
    query: str,
    top_k: int = 5,
) -> tuple[list[SearchResult], float, int]:
    """
    Embed query → cosine similarity search via pgvector.
    Returns (results, latency_ms, tokens_used).
    """
    t0 = time.monotonic()

    # Embed query
    query_embeddings, tokens = await embed_texts([query])
    query_vec = query_embeddings[0]

    # pgvector cosine similarity search
    supabase = get_supabase()

    # Using pgvector's <=> operator via RPC
    response = supabase.rpc("match_video_chunks", {
        "query_embedding": query_vec,
        "match_job_id": job_id,
        "match_count": top_k,
    }).execute()

    results = []
    for row in (response.data or []):
        results.append(SearchResult(
            chunk_id=row["chunk_id"],
            text=row["text"],
            similarity_score=round(1 - row["distance"], 4),  # pgvector returns distance
            start=row["start_time"],
            end=row["end_time"],
            speaker=row.get("speaker", "SPK_0"),
        ))

    latency = (time.monotonic() - t0) * 1000
    logger.info("search.done",
                query=query[:50],
                results=len(results),
                latency_ms=round(latency))

    return results, round(latency, 2), tokens


# ── Full embedding pipeline ────────────────────────────────────────────────────
async def embed_transcript(
    job_id: str,
    segments: list[TranscriptSegment],
) -> tuple[list[VectorChunk], int, float]:
    """
    Full pipeline: chunk → embed → store → return VectorChunk list.
    Returns (chunks, total_tokens, cost_usd).
    """
    raw_chunks = chunk_segments(segments)
    texts = [c["text"] for c in raw_chunks]

    embeddings, total_tokens = await embed_texts(texts)
    cost = total_tokens * COST_PER_TOKEN_EMBED

    await store_chunks(job_id, raw_chunks, embeddings)

    # Build VectorChunk objects (with embedding preview — first 8 dims only)
    vector_chunks = []
    for chunk, emb in zip(raw_chunks, embeddings):
        vector_chunks.append(VectorChunk(
            chunk_id=chunk["chunk_id"],
            text=chunk["text"],
            start=chunk["start"],
            end=chunk["end"],
            embedding_preview=[round(x, 4) for x in emb[:8]],
            similarity_score=None,
        ))

    logger.info("embed_transcript.done",
                chunks=len(vector_chunks),
                tokens=total_tokens,
                cost_usd=round(cost, 6))

    return vector_chunks, total_tokens, cost
