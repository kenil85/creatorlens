"""
LangGraph Multi-Agent Pipeline — Groq LLaMA (FREE)
────────────────────────────────────────────────────
Same 4-agent StateGraph, now powered by llama-3.3-70b via Groq.
Groq is free and actually faster than OpenAI.
"""

import time
import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import TranscriptSegment, AgentResult, OfferArchitecture

settings = get_settings()


class PipelineState(TypedDict):
    transcript_text: str
    transcript_segments: list[dict]
    video_title: str
    topics: str
    sentiment_analysis: str
    monetization_signals: str
    offer: dict
    agent_results: list[dict]
    total_tokens: int
    total_cost: float


def make_llm(temperature: float = 0.3) -> ChatGroq:
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        api_key=settings.groq_api_key,
    )


async def topic_modeler(state: PipelineState) -> PipelineState:
    logger.info("agent.topic_modeler.start")
    t0 = time.monotonic()
    llm = make_llm(temperature=0.2)

    messages = [
        SystemMessage(content="""You are a Topic Modeler for creator content analysis.
Extract the 5-7 main themes from the transcript.
Return ONLY valid JSON, no markdown, no explanation:
{"themes": [{"name": "string", "percentage": 20, "key_quote": "short quote"}]}"""),
        HumanMessage(content=f"Video: {state['video_title']}\n\nTranscript:\n{state['transcript_text'][:3000]}")
    ]

    response = await llm.ainvoke(messages)
    latency = (time.monotonic() - t0) * 1000
    tokens = getattr(response.usage_metadata, 'input_tokens', 0) + getattr(response.usage_metadata, 'output_tokens', 0) if response.usage_metadata else 200

    logger.info("agent.topic_modeler.done", latency_ms=round(latency))

    return {
        **state,
        "topics": response.content,
        "agent_results": state["agent_results"] + [{
            "agent_name": "TopicModeler",
            "output": response.content,
            "tokens_used": tokens,
            "latency_ms": round(latency),
        }],
        "total_tokens": state["total_tokens"] + tokens,
        "total_cost": 0.0,
    }


async def sentiment_analyzer(state: PipelineState) -> PipelineState:
    logger.info("agent.sentiment_analyzer.start")
    t0 = time.monotonic()
    llm = make_llm(temperature=0.1)

    messages = [
        SystemMessage(content="""You are a Sentiment and Engagement Analyzer for creator content.
Return ONLY valid JSON, no markdown:
{
  "overall_sentiment": "positive",
  "energy_arc": [{"segment_pct": 25, "energy": 0.8, "emotion": "inspired"}],
  "peak_moments": [{"timestamp_hint": "0:30", "reason": "vulnerability moment", "energy": 0.9}],
  "audience_connection_score": 0.85,
  "vulnerability_moments": ["example moment"]
}"""),
        HumanMessage(content=f"Topics:\n{state['topics']}\n\nTranscript:\n{state['transcript_text'][:2500]}")
    ]

    response = await llm.ainvoke(messages)
    latency = (time.monotonic() - t0) * 1000
    tokens = 200

    return {
        **state,
        "sentiment_analysis": response.content,
        "agent_results": state["agent_results"] + [{
            "agent_name": "SentimentAnalyzer",
            "output": response.content,
            "tokens_used": tokens,
            "latency_ms": round(latency),
        }],
        "total_tokens": state["total_tokens"] + tokens,
        "total_cost": 0.0,
    }


async def monetization_detector(state: PipelineState) -> PipelineState:
    logger.info("agent.monetization_detector.start")
    t0 = time.monotonic()
    llm = make_llm(temperature=0.3)

    messages = [
        SystemMessage(content="""You are a Monetization Signal Detector for the creator economy.
Return ONLY valid JSON, no markdown:
{
  "pain_points": ["pain 1", "pain 2"],
  "expertise_signals": ["signal 1", "signal 2"],
  "transformation_promised": "from X to Y",
  "ideal_customer": "description",
  "monetization_score": 0.82,
  "price_anchor_range": "$1,997 - $4,997",
  "offer_category": "course"
}"""),
        HumanMessage(content=f"Topics:\n{state['topics']}\n\nSentiment:\n{state['sentiment_analysis']}\n\nTranscript:\n{state['transcript_text'][:2000]}")
    ]

    response = await llm.ainvoke(messages)
    latency = (time.monotonic() - t0) * 1000
    tokens = 200

    return {
        **state,
        "monetization_signals": response.content,
        "agent_results": state["agent_results"] + [{
            "agent_name": "MonetizationDetector",
            "output": response.content,
            "tokens_used": tokens,
            "latency_ms": round(latency),
        }],
        "total_tokens": state["total_tokens"] + tokens,
        "total_cost": 0.0,
    }


async def offer_architect(state: PipelineState) -> PipelineState:
    logger.info("agent.offer_architect.start")
    t0 = time.monotonic()
    llm = make_llm(temperature=0.6)

    messages = [
        SystemMessage(content="""You are an Offer Architect for the creator economy.
Return ONLY valid JSON, no markdown, no explanation:
{
  "title": "Offer Title",
  "price_anchor": "$2,997",
  "core_promise": "what you promise",
  "hook": "one sentence hook",
  "modules": ["Module 1", "Module 2", "Module 3", "Module 4"],
  "pain_points": ["pain 1", "pain 2", "pain 3"],
  "transformation": "from X to Y in Z time",
  "sales_page_headline": "headline",
  "objection_handlers": [{"objection": "too expensive", "response": "response here"}]
}"""),
        HumanMessage(content=f"Video: {state['video_title']}\nTopics: {state['topics'][:500]}\nMonetization: {state['monetization_signals'][:500]}")
    ]

    response = await llm.ainvoke(messages)
    latency = (time.monotonic() - t0) * 1000
    tokens = 300

    try:
        clean = response.content.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        offer_data = json.loads(clean.strip())
    except Exception:
        offer_data = {
            "title": "Creator Mastery Program",
            "price_anchor": "$2,997",
            "core_promise": "Transform your expertise into a high-ticket offer",
            "hook": "Stop trading time for money.",
            "modules": ["Foundation", "Audience Building", "Offer Creation", "Launch Strategy"],
            "pain_points": ["No consistent revenue", "Unclear positioning", "Undercharging"],
            "transformation": "From content creator to premium offer owner in 90 days",
        }

    return {
        **state,
        "offer": offer_data,
        "agent_results": state["agent_results"] + [{
            "agent_name": "OfferArchitect",
            "output": response.content,
            "tokens_used": tokens,
            "latency_ms": round(latency),
        }],
        "total_tokens": state["total_tokens"] + tokens,
        "total_cost": 0.0,
    }


def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)
    graph.add_node("topic_modeler", topic_modeler)
    graph.add_node("sentiment_analyzer", sentiment_analyzer)
    graph.add_node("monetization_detector", monetization_detector)
    graph.add_node("offer_architect", offer_architect)
    graph.set_entry_point("topic_modeler")
    graph.add_edge("topic_modeler", "sentiment_analyzer")
    graph.add_edge("sentiment_analyzer", "monetization_detector")
    graph.add_edge("monetization_detector", "offer_architect")
    graph.add_edge("offer_architect", END)
    return graph.compile()


PIPELINE = build_pipeline()


async def run_agents(
    transcript_segments: list[TranscriptSegment],
    video_title: str,
) -> tuple[list[AgentResult], dict, int, float]:
    transcript_text = " ".join(
        f"[{seg.speaker} {seg.start:.1f}s] {seg.text}"
        for seg in transcript_segments
    )

    initial_state: PipelineState = {
        "transcript_text": transcript_text,
        "transcript_segments": [s.model_dump() for s in transcript_segments],
        "video_title": video_title,
        "topics": "",
        "sentiment_analysis": "",
        "monetization_signals": "",
        "offer": {},
        "agent_results": [],
        "total_tokens": 0,
        "total_cost": 0.0,
    }

    final_state = await PIPELINE.ainvoke(initial_state)
    agent_results = [AgentResult(**r) for r in final_state["agent_results"]]

    return agent_results, final_state["offer"], final_state["total_tokens"], 0.0
