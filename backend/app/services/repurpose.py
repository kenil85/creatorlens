"""
Content Repurposing Service — Groq LLaMA (FREE)
"""

import json
import time
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import ContentMap, TranscriptSegment

settings = get_settings()


def make_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        api_key=settings.groq_api_key,
    )


async def generate_content_map(
    segments: list[TranscriptSegment],
    offer: dict,
    video_title: str,
) -> tuple[ContentMap, int, float]:
    t0 = time.monotonic()
    llm = make_llm()

    transcript_text = " ".join(seg.text for seg in segments[:15])
    offer_title = offer.get("title", "Untitled Offer")
    offer_hook = offer.get("hook", "")

    messages = [
        SystemMessage(content="""You are a Content Strategist for the creator economy.
Return ONLY valid JSON, no markdown, no explanation:
{
  "twitter_thread": "Tweet 1/8: hook here\\n\\nTweet 2/8: point\\n\\nTweet 8/8: CTA with link",
  "email_subject": "subject line under 60 chars",
  "email_body": "Full email: Hook paragraph. Story paragraph. Value paragraph. CTA paragraph.",
  "short_form_clips": [
    {"title": "Clip title", "start_hint": "0:00", "end_hint": "0:60", "hook": "hook line"},
    {"title": "Clip title 2", "start_hint": "1:00", "end_hint": "2:00", "hook": "hook line 2"},
    {"title": "Clip title 3", "start_hint": "3:00", "end_hint": "4:00", "hook": "hook line 3"}
  ],
  "linkedin_angle": "Opening hook. Key insight 1. Key insight 2. Key insight 3. CTA."
}"""),
        HumanMessage(content=f"Video: {video_title}\nOffer: {offer_title}\nHook: {offer_hook}\nTranscript: {transcript_text[:1500]}")
    ]

    response = await llm.ainvoke(messages)
    latency = (time.monotonic() - t0) * 1000

    try:
        clean = response.content.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        data = json.loads(clean.strip())
        content_map = ContentMap(
            twitter_thread=data.get("twitter_thread", ""),
            email_subject=data.get("email_subject", ""),
            email_body=data.get("email_body", ""),
            short_form_clips=data.get("short_form_clips", []),
            linkedin_angle=data.get("linkedin_angle", ""),
        )
    except Exception as e:
        logger.warning("content_map.parse_failed", error=str(e))
        content_map = ContentMap(
            twitter_thread=f"Thread about {offer_title}...",
            email_subject=f"New: {offer_title}",
            email_body=response.content[:500],
            short_form_clips=[],
            linkedin_angle="",
        )

    logger.info("content_map.done", latency_ms=round(latency), cost="$0.00")
    return content_map, 300, 0.0
