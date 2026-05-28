from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import PipelineRequest, PipelineResult
from app.services.pipeline import run_pipeline_stream, get_job
from app.core.security import rate_limit, fingerprint_request
from app.core.logging import logger
from fastapi import Request

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
async def run_pipeline(
    body: PipelineRequest,
    request: Request,
    _: None = Depends(rate_limit),
):
    """
    Start the video intelligence pipeline.
    Returns a Server-Sent Event stream.
    Each event has: event, stage, data, message, progress.
    """
    fp = fingerprint_request(request)
    logger.info("pipeline.run.request", url=body.video_url, fingerprint=fp)

    return StreamingResponse(
        run_pipeline_stream(body.video_url),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",       # Important for nginx proxies
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/job/{job_id}", response_model=PipelineResult)
async def get_pipeline_result(job_id: str):
    """Get the full result of a completed pipeline job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
