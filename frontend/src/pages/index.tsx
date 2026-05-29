'use client'

import { useRef } from 'react'
import { motion } from 'framer-motion'
import { usePipelineStore } from '@/lib/store'
import { runPipeline } from '@/lib/api'
import StageCard from '@/components/StageCard'
import {
  AgentGraph,
  TranscriptViewer,
  VectorGrid,
  SemanticSearch,
  OfferCard,
  ContentMap,
} from '@/components/PipelineComponents'
import {
  MetricsPanel,
  CostTracker,
  LiveLog,
  ArchDiagram,
} from '@/components/SidebarComponents'
import { Github, Linkedin, Play, RotateCcw } from 'lucide-react'

const PRESETS = [
  { label: 'Jay Shetty — Purpose',  url: 'https://www.youtube.com/watch?v=TzaZMQpNInw' },
  { label: 'Kiyosaki — Wealth',     url: 'https://www.youtube.com/watch?v=W92QGmMjmAY' },
  { label: 'Belfort — Sales',       url: 'https://www.youtube.com/watch?v=7IE9Cg_Qb6Y' },
]

export default function Home() {
  const {
    videoUrl, setVideoUrl,
    isRunning, jobId, stages,
    startPipeline, handleEvent, reset,
  } = usePipelineStore()

  const cancelRef = useRef<(() => void) | null>(null)

  const handleRun = () => {
    if (!videoUrl.trim()) return
    startPipeline()
    cancelRef.current = runPipeline(
      videoUrl,
      handleEvent,
      (err) => handleEvent({ event: 'error', message: err }),
    )
  }

  const handleReset = () => {
    cancelRef.current?.()
    reset()
  }

  return (
    <div className="min-h-screen bg-surface-0 font-sans">

      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-border">
        <div className="max-w-screen-xl mx-auto px-6 py-4 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-brand-500 flex items-center justify-center text-white text-sm font-bold">
              CL
            </div>
            <div>
              <div className="font-serif text-xl leading-none">CreatorLens</div>
              <div className="text-[10px] font-mono text-gray-400 uppercase tracking-widest mt-0.5">
                Video Intelligence Engine
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <a href="https://github.com/kenil0509" target="_blank"
               className="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-full border border-border hover:bg-surface-1 transition-colors text-gray-500">
              <Github size={12} /> kenil0509
            </a>
            <a href="https://www.linkedin.com/in/kenil-sutariya-39b277213/" target="_blank"
               className="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-full border border-border hover:bg-surface-1 transition-colors text-gray-500">
              <Linkedin size={12} /> Kenil Sutariya
            </a>
            <span className="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-full bg-brand-500 text-white">
              Applying @ CreatorJoy
            </span>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-screen-xl mx-auto px-6 py-12 border-b border-border">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 border border-brand-200 text-brand-500 text-xs font-mono uppercase tracking-wider mb-5">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
            LangGraph · pgvector · Whisper · FastAPI · Next.js
          </div>
          <h1 className="font-serif text-4xl md:text-5xl leading-tight tracking-tight mb-4">
            Your video content,<br />
            <span className="italic text-brand-500">intelligently decoded.</span>
          </h1>
          <p className="text-gray-500 text-lg max-w-2xl leading-relaxed">
            A production-grade multi-agent pipeline that transcribes, analyzes, embeds,
            and extracts monetization signals from creator content.
          </p>
        </motion.div>
      </section>

      {/* Input */}
      <section className="max-w-screen-xl mx-auto px-6 py-8 border-b border-border">
        <div className="text-[10px] font-mono uppercase tracking-widest text-gray-400 mb-4 flex items-center gap-3">
          Pipeline Input <span className="flex-1 h-px bg-border" />
        </div>
        <div className="flex gap-3 mb-3 flex-wrap">
          <input
            value={videoUrl}
            onChange={e => setVideoUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleRun()}
            placeholder="https://youtube.com/watch?v=..."
            disabled={isRunning}
            className="flex-1 min-w-0 font-mono text-sm px-4 py-3 rounded-xl border border-border bg-surface-1 focus:outline-none focus:border-brand-500 focus:bg-white transition-colors placeholder:text-gray-400 disabled:opacity-50"
          />
          {!isRunning ? (
            <button onClick={handleRun} disabled={!videoUrl.trim()}
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
              <Play size={14} /> Run Pipeline
            </button>
          ) : (
            <button onClick={handleReset}
              className="flex items-center gap-2 px-6 py-3 rounded-xl border border-border text-sm text-gray-500 hover:bg-surface-1 transition-colors">
              <RotateCcw size={14} /> Reset
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map(p => (
            <button key={p.label} onClick={() => setVideoUrl(p.url)} disabled={isRunning}
              className="text-xs font-mono px-3 py-1.5 rounded-lg border border-border bg-surface-1 text-gray-500 hover:border-brand-200 hover:text-brand-500 hover:bg-brand-50 transition-colors disabled:opacity-40">
              {p.label}
            </button>
          ))}
        </div>
      </section>

      {/* Main */}
      <div className="max-w-screen-xl mx-auto px-6 py-8 grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-8">

        <div className="space-y-4">

          <StageCard title="Stage 1 — Ingestion + Transcription"
            subtitle="yt-dlp · Groq Whisper · Speaker diarization"
            icon="📥" status={stages.ingestion.status}
            progress={stages.ingestion.progress} message={stages.ingestion.message}>
            <TranscriptViewer />
          </StageCard>

          <StageCard title="Stage 2 — LangGraph Multi-Agent Analysis"
            subtitle="StateGraph · 4 agents · Groq LLaMA-3.3-70b"
            icon="🧠" status={stages.agents.status}
            progress={stages.agents.progress} message={stages.agents.message}>
            <AgentGraph />
          </StageCard>

          <StageCard title="Stage 3 — Chunking + Vector Embedding"
            subtitle="sentence-transformers · pgvector · cosine similarity"
            icon="🔢" status={stages.embedding.status}
            progress={stages.embedding.progress} message={stages.embedding.message}>
            <VectorGrid />
          </StageCard>

          <StageCard title="Stage 4 — Semantic Search"
            subtitle="pgvector cosine search · prompt injection defense"
            icon="🔍"
            status={stages.embedding.status === 'done' ? 'done' : 'idle'}
            progress={stages.embedding.status === 'done' ? 100 : 0}
            message={stages.embedding.status === 'done' ? 'Ready to search' : 'Run pipeline to enable'}>
            <SemanticSearch />
          </StageCard>

          <StageCard title="Stage 5 — Creator Intelligence Output"
            subtitle="Offer architecture · content repurposing · monetization map"
            icon="✨" status={stages.repurpose.status}
            progress={stages.repurpose.progress} message={stages.repurpose.message}>
            <div className="space-y-4">
              <OfferCard />
              <ContentMap />
            </div>
          </StageCard>

        </div>

        <div className="space-y-5">
          <MetricsPanel />
          <CostTracker />
          <LiveLog />
          <ArchDiagram />
        </div>

      </div>
    </div>
  )
}