'use client'

import { usePipelineStore } from '@/lib/store'
import { motion } from 'framer-motion'
import clsx from 'clsx'

// ─────────────────────────────────────────────────────────────
// MetricsPanel
// ─────────────────────────────────────────────────────────────
export function MetricsPanel() {
  const { totalTokens, totalLatencyMs, chunks, monetizationScore } = usePipelineStore()

  const metrics = [
    { label: 'Latency',  value: totalLatencyMs ? `${totalLatencyMs}ms` : '—' },
    { label: 'Tokens',   value: totalTokens    ? totalTokens.toLocaleString() : '—' },
    { label: 'Chunks',   value: chunks.length  ? String(chunks.length) : '—' },
    { label: 'Mono.',    value: monetizationScore ? monetizationScore.toFixed(2) : '—' },
  ]

  return (
    <div>
      <SectionLabel>Live Metrics</SectionLabel>
      <div className="grid grid-cols-2 gap-2">
        {metrics.map(m => (
          <div key={m.label} className="p-3 rounded-xl bg-surface-1 border border-border text-center">
            <div className="text-xl font-medium text-gray-900 leading-none mb-1">{m.value}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-gray-400">{m.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// CostTracker
// ─────────────────────────────────────────────────────────────
export function CostTracker() {
  const { stages, totalCostUsd } = usePipelineStore()

  const whisperCost = stages.ingestion.data?.cost_usd  || 0
  const agentCost   = stages.agents.data?.cost_usd     || 0
  const embedCost   = stages.embedding.data?.cost_usd  || 0

  const rows = [
    { label: 'Whisper (transcription)', val: whisperCost },
    { label: 'Embeddings (ada-002)',     val: embedCost },
    { label: 'LLM inference (agents)',   val: agentCost },
  ]

  return (
    <div>
      <SectionLabel>Cost Tracking</SectionLabel>
      <div className="rounded-xl border border-border overflow-hidden">
        {rows.map((r, i) => (
          <div key={r.label} className={clsx(
            'flex items-center justify-between px-3 py-2.5 text-xs',
            i < rows.length - 1 && 'border-b border-border'
          )}>
            <span className="text-gray-500">{r.label}</span>
            <motion.span
              key={r.val}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="font-mono text-gray-700"
            >
              ${r.val.toFixed(5)}
            </motion.span>
          </div>
        ))}
        <div className="flex items-center justify-between px-3 py-2.5 text-xs bg-surface-1 border-t border-border font-medium">
          <span className="text-gray-700">Total</span>
          <motion.span key={totalCostUsd} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="font-mono">
            ${totalCostUsd.toFixed(5)}
          </motion.span>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// LiveLog
// ─────────────────────────────────────────────────────────────
export function LiveLog() {
  const { logs } = usePipelineStore()

  return (
    <div>
      <SectionLabel>Structured Log</SectionLabel>
      <div className="rounded-xl border border-border bg-surface-1 p-3 max-h-48 overflow-y-auto space-y-1">
        {logs.length === 0 && (
          <div className="text-[11px] font-mono text-gray-400 italic">Waiting for pipeline...</div>
        )}
        {logs.map((log, i) => (
          <div key={i} className="flex gap-2 text-[11px] font-mono leading-relaxed">
            <span className="text-gray-400 flex-shrink-0">{log.time}</span>
            <span className={clsx(
              log.level === 'error' ? 'text-red-500' :
              log.level === 'warn'  ? 'text-amber-500' :
              'text-emerald-600'
            )}>
              {log.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// ArchDiagram
// ─────────────────────────────────────────────────────────────
const ARCH_NODES = [
  { label: 'Ingestion Layer',  sublabel: 'yt-dlp · Whisper',       color: 'blue'   },
  { label: 'LangGraph Agents', sublabel: '4 agents · StateGraph',   color: 'purple' },
  { label: 'Vector Store',     sublabel: 'pgvector · ada-002',      color: 'teal'   },
  { label: 'Security Layer',   sublabel: 'injection defense',       color: 'amber'  },
  { label: 'Streaming Output', sublabel: 'SSE · FastAPI',           color: 'green'  },
]

const dotColors: Record<string, string> = {
  blue:   'bg-blue-400',
  purple: 'bg-brand-500',
  teal:   'bg-emerald-400',
  amber:  'bg-amber-400',
  green:  'bg-green-400',
}

export function ArchDiagram() {
  return (
    <div>
      <SectionLabel>System Architecture</SectionLabel>
      <div className="rounded-xl border border-border overflow-hidden">
        {ARCH_NODES.map((node, i) => (
          <div key={node.label}>
            <div className="flex items-center gap-3 px-3 py-2.5 hover:bg-surface-1 transition-colors cursor-pointer text-xs group">
              <div className={clsx('w-2 h-2 rounded-full flex-shrink-0', dotColors[node.color])} />
              <span className="text-gray-800 font-medium flex-1">{node.label}</span>
              <span className="font-mono text-[10px] text-gray-400">{node.sublabel}</span>
            </div>
            {i < ARCH_NODES.length - 1 && (
              <div className="w-px h-3 bg-border ml-4" />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Shared
// ─────────────────────────────────────────────────────────────
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 mb-3">
      <span className="text-[10px] font-mono uppercase tracking-widest text-gray-400">{children}</span>
      <span className="flex-1 h-px bg-border" />
    </div>
  )
}

export default MetricsPanel
