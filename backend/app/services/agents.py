"""
LangGraph Multi-Agent Pipeline
───────────────────────────────
StateGraph with 4 specialized agents:

  [START]
     │
     ▼
 TopicModeler ──► SentimentAnalyzer ──► MonetizationDetector ──► OfferArchitect
                                                                       │
                                                                    [END]

Each agent reads from shared state, writes its output back,
and passes enriched context to the next node.
"""

import time
import json
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from app.core.config import get_settings
from app.core.logging import logger
from app.models.schemas import TranscriptSegment, AgentResult, OfferArchitecture

settings = get_settings()

# ── Shared state schema ────────────────────────────────────────────────────────
class PipelineState(TypedDict):
    transcript_text: str
    transcript_segments: list[dict]
    video_title: str

    # Agent outputs
    topics: str
    sentiment_analysis: str
    monetization_signals: str
    offer: dict

    # Accumulated results
    agent_results: list[dict]
    total_tokens: int
    total_cost: float


# ── LLM factory ───────────────────────────────────────────────────────────────
def make_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=temperature,
        api_key=settings.openai_api_key,
    )


COST_PER_INPUT_TOKEN = 0.00000015   # gpt-4o-mini
COST_PER_OUTPUT_TOKEN = 0.0000006


def calc_cost(usage) -> float:
    if not usage:
        return 0.0
    return (
        usage.prompt_tokens * COST_PER_INPUT_TOKEN +
        usage.completion_tokens * COST_PER_OUTPUT_TOKEN
    )


# ── Agent 1: Topic Modeler ─────────────────────────────────────────────────────
async def topic_modeler(state: PipelineState) -> PipelineState:
    logger.info("agent.topic_modeler.start")
    t0 = time.monotonic()
    llm = make_llm(temperature=0.2)

    messages = [
        SystemMessage(content="""You are a Topic Modeler for creator content analysis.
Extract the 5-7 main themes from the transcript.
For each theme: name, percentage of content, key quotes (max 10 words each).
Return as JSON: {"themes": [{"name": str, "percentage": int, "key_quote": str}]}
Be precise and data-driven."""),
        HumanMessage(content=f"Video: {state['video_title']}\n\nTranscript:\n{state['transcript_text'][:3000]}")
    ]

    response = await llm.ainvoke(messages)
    latency = (time.monotonic() - t0) * 1000
    cost = calc_cost(response.usage_metadata)
    tokens = (response.usage_metadata.input_tokens + response.usage_metadata.output_tokens) if response.usage_metadata else 0

    logger.info("agent.topic_modeler.done", tokens=tokens, latency_ms=round(latency))

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
        "total_cost": state["total_cost"] + cost,
    }


# ── Agent 2: Sentiment Analyzer ────────────────────────────────────────────────
async def sentiment_analyzer(state: PipelineState) -> PipelineState:
    logger.info("agent.sentiment_analyzer.start")
    t0 = time.monotonic()
    llm = make_llm(temperature=0.1)

    messages = [
        SystemMessage(content="""You are a Sentiment and Engagement Analyzer for creator content.
Analyze emotional arc, engagement peaks, and audience connection moments.
Return JSON: {
  "overall_sentiment": "positive|negative|mixed",
  "energy_arc": [{"segment_pct": int, "energy": float_0_to_1, "emotion": str}],
  "peak_moments": [{"timestamp_hint": str, "reason": str, "energy": float}],
  "audience_connection_score": float_0_to_1,
  "vulnerability_moments": [str]
}"""),
        HumanMessage(content=f"Topics identified:\n{state['topics']}\n\nTranscript:\n{state['transcript_text'][:3000]}")
    ]

    response = await llm.ainvoke(messages)
    latency = (time.monotonic() - t0) * 1000
    cost = calc_cost(response.usage_metadata)
    tokens = (response.usage_metadata.input_tokens + response.usage_metadata.output_tokens) if response.usage_metadata else 0

    logger.info("agent.sentiment_analyzer.done", tokens=tokens, latency_ms=round(latency))

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
        "total_cost": state["total_cost"] + cost,
    }


# ── Agent 3: Monetization Detector ────────────────────────────────────────────
async def monetization_detector(state: PipelineState) -> PipelineState:
    logger.info("agent.monetization_detector.start")
    t0 = time.monotonic()
    llm = make_llm(temperature=0.3)

    messages = [
        SystemMessage(content="""You are a Monetization Signal Detector for the creator economy.
Identify what problems the creator solves, their unique expertise, and high-ticket offer potential.
Return JSON: {
  "pain_points": [str],
  "expertise_signals": [str],
  "transformation_promised": str,
  "ideal_customer": str,
  "monetization_score": float_0_to_1,
  "price_anchor_range": str,
  "offer_category": "course|coaching|mastermind|community|productized_service"
}"""),
        HumanMessage(content=f"Topics:\n{state['topics']}\n\nSentiment:\n{state['sentiment_analysis']}\n\nTranscript:\n{state['transcript_text'][:2000]}")
    ]

    response = await llm.ainvoke(messages)
    latency = (time.monotonic() - t0) * 1000
    cost = calc_cost(response.usage_metadata)
    tokens = (response.usage_metadata.input_tokens + response.usage_metadata.output_tokens) if response.usage_metadata else 0

    logger.info("agent.monetization_detector.done", tokens=tokens, latency_ms=round(latency))

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
        "total_cost": state["total_cost"] + cost,
    }


# ── Agent 4: Offer Architect ───────────────────────────────────────────────────
async def offer_architect(state: PipelineState) -> PipelineState:
    logger.info("agent.offer_architect.start")
    t0 = time.monotonic()
    llm = make_llm(temperature=0.6)  # More creative for offer naming

    messages = [
        SystemMessage(content="""You are an Offer Architect for the creator economy.
Design a complete high-ticket offer structure based on all analysis.
Return JSON: {
  "title": str,
  "price_anchor": str,
  "core_promise": str,
  "hook": str,
  "modules": [str, str, str, str],
  "pain_points": [str, str, str],
  "transformation": str,
  "sales_page_headline": str,
  "objection_handlers": [{"objection": str, "response": str}]
}
Make it specific, compelling, and premium-priced ($1k–$10k range)."""),
        HumanMessage(content=f"""
Video Title: {state['video_title']}
Topics: {state['topics']}
Sentiment: {state['sentiment_analysis']}
Monetization Signals: {state['monetization_signals']}
""")
    ]

    response = await llm.ainvoke(messages)
    latency = (time.monotonic() - t0) * 1000
    cost = calc_cost(response.usage_metadata)
    tokens = (response.usage_metadata.input_tokens + response.usage_metadata.output_tokens) if response.usage_metadata else 0

    # Parse offer JSON
    try:
        clean = response.content.strip().lstrip("```json").rstrip("```").strip()
        offer_data = json.loads(clean)
    except Exception:
        offer_data = {"title": "Offer Generation Failed", "raw": response.content}

    logger.info("agent.offer_architect.done", tokens=tokens, latency_ms=round(latency))

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
        "total_cost": state["total_cost"] + cost,
    }


# ── Build the StateGraph ───────────────────────────────────────────────────────
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
    """
    Run the full LangGraph pipeline.
    Returns (agent_results, offer_dict, total_tokens, total_cost)
    """
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

    return (
        agent_results,
        final_state["offer"],
        final_state["total_tokens"],
        final_state["total_cost"],
    )
