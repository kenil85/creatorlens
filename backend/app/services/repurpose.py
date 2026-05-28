"""
Content Repurposing Service
────────────────────────────
Given transcript + offer data, generates:
- Twitter/X thread
- Email newsletter (subject + body)
- Short-form clip timestamps
- LinkedIn article angle
"""

import json
import time
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import ContentMap, TranscriptSegment

settings = get_settings()


def make_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=settings.openai_api_key,
    )


async def generate_content_map(
    segments: list[TranscriptSegment],
    offer: dict,
    video_title: str,
) -> tuple[ContentMap, int, float]:
    """Generate all content formats from transcript + offer."""
    t0 = time.monotonic()
    llm = make_llm()

    transcript_text = " ".join(seg.text for seg in segments[:20])  # First 20 segments
    offer_title = offer.get("title", "Untitled Offer")
    offer_hook = offer.get("hook", "")

    messages = [
        SystemMessage(content="""You are a Content Strategist for the creator economy.
Generate repurposed content for all platforms from the transcript.
Return ONLY valid JSON in this exact format:
{
  "twitter_thread": "Tweet 1/8: [hook]\\n\\nTweet 2/8: [point]\\n\\n... Tweet 8/8: [CTA]",
  "email_subject": "subject line under 60 chars",
  "email_body": "Full email body with sections: Hook, Story, Value, CTA",
  "short_form_clips": [
    {"title": str, "start_hint": str, "end_hint": str, "hook": str},
    {"title": str, "start_hint": str, "end_hint": str, "hook": str},
    {"title": str, "start_hint": str, "end_hint": str, "hook": str}
  ],
  "linkedin_angle": "Opening line + 3 key insights + CTA for LinkedIn article"
}"""),
        HumanMessage(content=f"""
Video: {video_title}
Offer: {offer_title}
Hook: {offer_hook}
Transcript excerpt: {transcript_text[:2000]}
""")
    ]

    response = await llm.ainvoke(messages)
    latency = (time.monotonic() - t0) * 1000
    tokens = (response.usage_metadata.input_tokens + response.usage_metadata.output_tokens) if response.usage_metadata else 0
    cost = tokens * 0.00000015

    # Parse response
    try:
        clean = response.content.strip().lstrip("```json").rstrip("```").strip()
        data = json.loads(clean)
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
            twitter_thread=response.content[:500],
            email_subject=f"{offer_title} — New Content",
            email_body="Content generation in progress...",
            short_form_clips=[],
            linkedin_angle="",
        )

    logger.info("content_map.done", tokens=tokens, latency_ms=round(latency))
    return content_map, tokens, cost
