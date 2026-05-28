from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import SearchRequest, SearchResponse
from app.services.vectorstore import semantic_search
from app.services.pipeline import get_job
from app.core.security import rate_limit, detect_injection, sanitize_input
from app.core.logging import logger

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    _: None = Depends(rate_limit),
):
    """
    Semantic search over a completed pipeline job's embedded chunks.
    Includes prompt injection defense.
    """
    # Sanitize input
    query = sanitize_input(body.query)

    # Injection detection
    is_injection, matched = detect_injection(query)
    if is_injection:
        logger.warning("search.injection_blocked", pattern=matched, query=query[:80])
        return SearchResponse(
            query=query,
            results=[],
            injection_detected=True,
            latency_ms=0.0,
        )

    # Verify job exists
    job = get_job(body.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found. Run the pipeline first.")

    results, latency_ms, _ = await semantic_search(
        job_id=body.job_id,
        query=query,
        top_k=body.top_k,
    )

    logger.info("search.complete",
                job_id=body.job_id,
                query=query[:50],
                results=len(results),
                latency_ms=latency_ms)

    return SearchResponse(
        query=query,
        results=results,
        injection_detected=False,
        latency_ms=latency_ms,
    )
