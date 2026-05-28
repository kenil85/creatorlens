from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class PipelineStatus(str, Enum):
    QUEUED = "queued"
    INGESTING = "ingesting"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    EMBEDDING = "embedding"
    COMPLETE = "complete"
    ERROR = "error"


class PipelineRequest(BaseModel):
    video_url: str = Field(..., min_length=10, max_length=500)

    @field_validator("video_url")
    @classmethod
    def must_be_video_url(cls, v: str) -> str:
        from app.core.security import validate_video_url
        if not validate_video_url(v):
            raise ValueError("URL must be from YouTube or Vimeo")
        return v


class TranscriptSegment(BaseModel):
    speaker: str
    start: float
    end: float
    text: str


class AgentResult(BaseModel):
    agent_name: str
    output: str
    tokens_used: int
    latency_ms: float


class VectorChunk(BaseModel):
    chunk_id: str
    text: str
    start: float
    end: float
    embedding_preview: list[float]  # first 8 dims only for display
    similarity_score: Optional[float] = None


class OfferArchitecture(BaseModel):
    title: str
    price_anchor: str
    core_promise: str
    hook: str
    modules: list[str]
    pain_points: list[str]
    transformation: str


class ContentMap(BaseModel):
    twitter_thread: str
    email_subject: str
    email_body: str
    short_form_clips: list[dict]
    linkedin_angle: str


class PipelineResult(BaseModel):
    job_id: str
    status: PipelineStatus
    video_url: str
    video_title: Optional[str] = None
    duration_seconds: Optional[float] = None

    # Stage outputs
    transcript: list[TranscriptSegment] = []
    agent_results: list[AgentResult] = []
    chunks: list[VectorChunk] = []
    offer: Optional[OfferArchitecture] = None
    content_map: Optional[ContentMap] = None

    # Metrics
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    monetization_score: float = 0.0

    error: Optional[str] = None


class SearchRequest(BaseModel):
    job_id: str
    query: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    chunk_id: str
    text: str
    similarity_score: float
    start: float
    end: float
    speaker: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    injection_detected: bool = False
    latency_ms: float = 0.0


class PipelineEvent(BaseModel):
    """Server-Sent Event payload for streaming pipeline progress."""
    event: str  # stage_start | stage_done | agent_update | log | complete | error
    stage: Optional[str] = None
    data: Optional[dict] = None
    message: Optional[str] = None
    progress: Optional[float] = None  # 0-100
