"""
Vector Embedding — sentence-transformers (FREE, local)
───────────────────────────────────────────────────────
Uses all-MiniLM-L6-v2 — runs locally, no API key, no cost.
384-dim embeddings, great for semantic search.
"""

import time
import uuid
import math
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import TranscriptSegment, VectorChunk, SearchResult

settings = get_settings()

# Load once at startup — downloads ~90MB first time, cached after
_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("embedding_model.loading", model="all-MiniLM-L6-v2")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("embedding_model.ready")
    return _model

EMBEDDING_DIMS = 384  # all-MiniLM-L6-v2 output dims


def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


def chunk_segments(
    segments: list[TranscriptSegment],
    chunk_size: int = 3,
    overlap: int = 1,
) -> list[dict]:
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
        })

    return chunks


def embed_texts_local(texts: list[str]) -> list[list[float]]:
    """Embed using local sentence-transformers. Free, no API call."""
    t0 = time.monotonic()
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True).tolist()
    latency = (time.monotonic() - t0) * 1000
    logger.info("embed.done", count=len(texts), latency_ms=round(latency), cost="$0.00")
    return embeddings


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


async def store_chunks(
    job_id: str,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> None:
    try:
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
                "embedding": emb,
            })

        batch_size = 50
        for i in range(0, len(rows), batch_size):
            result = supabase.table("video_chunks").upsert(rows[i: i + batch_size]).execute()
            logger.info("pgvector.stored", batch=i // batch_size + 1, count=len(rows[i: i + batch_size]))

    except Exception as e:
        import traceback
        logger.error("pgvector.store_failed", error=str(e), traceback=traceback.format_exc())
        raise

async def semantic_search(
    job_id: str,
    query: str,
    top_k: int = 5,
) -> tuple[list[SearchResult], float, int]:
    t0 = time.monotonic()

    # Embed query locally
    query_embeddings = embed_texts_local([query])
    query_vec = query_embeddings[0]

    # Fetch all chunks for this job and rank by cosine similarity
    # (For production, use pgvector RPC — for free tier this is fine)
    supabase = get_supabase()
    response = supabase.table("video_chunks").select(
        "chunk_id, text, start_time, end_time, speaker, embedding"
    ).eq("job_id", job_id).execute()

    rows = response.data or []

    # Score each chunk
    scored = []
    for row in rows:
        emb = row["embedding"]
        if isinstance(emb, str):
            import json
            emb = json.loads(emb)
        emb = [float(x) for x in emb]
        score = cosine_similarity(query_vec, emb)
        scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    results = [
        SearchResult(
            chunk_id=row["chunk_id"],
            text=row["text"],
            similarity_score=round(score, 4),
            start=row["start_time"],
            end=row["end_time"],
            speaker=row.get("speaker", "SPK_0"),
        )
        for score, row in top
    ]

    latency = (time.monotonic() - t0) * 1000
    logger.info("search.done", results=len(results), latency_ms=round(latency))
    return results, round(latency, 2), 0


async def embed_transcript(
    job_id: str,
    segments: list[TranscriptSegment],
) -> tuple[list[VectorChunk], int, float]:
    raw_chunks = chunk_segments(segments)
    texts = [c["text"] for c in raw_chunks]

    embeddings = embed_texts_local(texts)

    await store_chunks(job_id, raw_chunks, embeddings)

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

    logger.info("embed_transcript.done", chunks=len(vector_chunks), cost="$0.00")
    return vector_chunks, len(texts) * 50, 0.0  # tokens approx, cost = 0
