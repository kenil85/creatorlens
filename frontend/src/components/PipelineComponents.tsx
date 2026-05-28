// ─────────────────────────────────────────────────────────────
// AgentGraph.tsx
// ─────────────────────────────────────────────────────────────
'use client'
import { usePipelineStore } from '@/lib/store'
import { motion } from 'framer-motion'
import clsx from 'clsx'

export function AgentGraph() {
  const { agents, agentResults } = usePipelineStore()

  return (
    <div className="space-y-3">
      {/* Agent nodes */}
      <div className="flex flex-wrap gap-2">
        {agents.map((agent, i) => (
          <motion.div
            key={agent.name}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1 }}
            className={clsx(
              'flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-mono transition-all',
              agent.status === 'firing' && 'bg-brand-50 border-brand-200 text-brand-500 animate-pulse',
              agent.status === 'done'   && 'bg-emerald-50 border-emerald-200 text-emerald-600',
              agent.status === 'idle'   && 'bg-surface-1 border-border text-gray-400',
            )}
          >
            <span className={clsx(
              'w-2 h-2 rounded-full',
              agent.status === 'firing' ? 'bg-brand-500' :
              agent.status === 'done'   ? 'bg-emerald-500' : 'bg-gray-300'
            )} />
            {agent.name}
          </motion.div>
        ))}
      </div>

      {/* Agent outputs */}
      {agentResults.length > 0 && (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {agentResults.map((r: any, i: number) => (
            <motion.div
              key={r.agent_name}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="p-3 rounded-xl bg-surface-1 border border-border"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-brand-500 font-medium">{r.agent_name}</span>
                <div className="flex gap-3 text-[10px] font-mono text-gray-400">
                  <span>{r.tokens_used} tokens</span>
                  <span>{r.latency_ms}ms</span>
                </div>
              </div>
              <pre className="text-xs text-gray-600 whitespace-pre-wrap break-words font-mono leading-relaxed max-h-32 overflow-y-auto">
                {r.output.substring(0, 400)}{r.output.length > 400 ? '...' : ''}
              </pre>
            </motion.div>
          ))}
        </div>
      )}

      {agentResults.length === 0 && (
        <p className="text-xs font-mono text-gray-400 italic">Agent outputs will stream here...</p>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// TranscriptViewer.tsx
// ─────────────────────────────────────────────────────────────
export function TranscriptViewer() {
  const { transcript } = usePipelineStore()

  if (!transcript.length) {
    return <p className="text-xs font-mono text-gray-400 italic">Transcript will appear here...</p>
  }

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
      {transcript.map((seg: any, i: number) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -4 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.03 }}
          className="flex gap-2 items-baseline"
        >
          <span className={clsx(
            'text-[10px] font-mono px-2 py-0.5 rounded border flex-shrink-0',
            seg.speaker === 'SPK_0'
              ? 'bg-blue-50 text-blue-600 border-blue-200'
              : 'bg-amber-50 text-amber-600 border-amber-200'
          )}>
            {seg.speaker}
          </span>
          <span className="text-[10px] font-mono text-gray-400 flex-shrink-0">[{seg.start}s]</span>
          <span className="text-xs text-gray-600 leading-relaxed">{seg.text}</span>
        </motion.div>
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// VectorGrid.tsx
// ─────────────────────────────────────────────────────────────
export function VectorGrid() {
  const { chunks } = usePipelineStore()

  if (!chunks.length) {
    return <p className="text-xs font-mono text-gray-400 italic">Embedded chunks will appear here...</p>
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {chunks.map((chunk: any, i: number) => (
          <motion.div
            key={chunk.chunk_id}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            className="p-2.5 rounded-xl border border-brand-200 bg-brand-50/50 hover:bg-brand-50 transition-colors cursor-default"
            title={chunk.text}
          >
            <div className="text-[11px] text-gray-700 truncate mb-1">{chunk.text.substring(0, 40)}...</div>
            <div className="text-[10px] font-mono text-gray-400">{chunk.start}s → {chunk.end}s</div>
            {chunk.similarity_score && (
              <div className="text-[10px] font-mono text-brand-500 mt-1">
                sim: {chunk.similarity_score.toFixed(3)}
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Embedding preview */}
      {chunks[0]?.embedding_preview && (
        <div className="p-3 rounded-xl bg-surface-1 border border-border">
          <div className="text-[10px] font-mono text-gray-400 mb-2">
            Embedding preview (first 8 dims of 1536):
          </div>
          <div className="flex gap-1 flex-wrap">
            {chunks[0].embedding_preview.map((v: number, i: number) => (
              <span key={i} className="text-[10px] font-mono px-1.5 py-0.5 bg-surface-2 rounded text-gray-500">
                {v.toFixed(4)}
              </span>
            ))}
            <span className="text-[10px] font-mono text-gray-400">… +1528 dims</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// SemanticSearch.tsx
// ─────────────────────────────────────────────────────────────
export function SemanticSearch() {
  const {
    jobId, searchQuery, setSearchQuery,
    searchResults, searchLatency, injectionDetected,
    isSearching, runSearch, stages,
  } = usePipelineStore()

  const isReady = stages.embedding.status === 'done' && !!jobId

  const handleSearch = () => {
    if (!jobId || !searchQuery.trim()) return
    runSearch(jobId, searchQuery)
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="what does the creator say about mindset?"
          disabled={!isReady}
          className="flex-1 text-xs font-mono px-3 py-2.5 rounded-xl border border-border-strong bg-surface-1 focus:outline-none focus:border-brand-500 focus:bg-white transition-colors placeholder:text-gray-400 disabled:opacity-50"
        />
        <button
          onClick={handleSearch}
          disabled={!isReady || isSearching || !searchQuery.trim()}
          className="px-4 py-2 rounded-xl bg-brand-500 text-white text-xs font-medium hover:bg-brand-600 disabled:opacity-40 transition-colors"
        >
          {isSearching ? '...' : 'Search'}
        </button>
      </div>

      {injectionDetected && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-50 border border-red-200 text-red-600 text-xs font-mono"
        >
          🛡️ Prompt injection attempt detected and blocked. Input sanitized.
        </motion.div>
      )}

      {searchResults.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] font-mono text-gray-400">
            {searchResults.length} results · {searchLatency.toFixed(0)}ms
          </div>
          {searchResults.map((r: any, i: number) => (
            <motion.div
              key={r.chunk_id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="p-3 rounded-xl border border-border bg-surface-1 hover:border-brand-200 hover:bg-brand-50/30 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-mono text-gray-400">
                  {r.speaker} · {r.start}s → {r.end}s
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-600">
                  {r.similarity_score.toFixed(4)}
                </span>
              </div>
              <p className="text-xs text-gray-700 leading-relaxed">{r.text}</p>
            </motion.div>
          ))}
        </div>
      )}

      {!isReady && (
        <p className="text-xs font-mono text-gray-400 italic">Run the pipeline first to enable semantic search...</p>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// OfferCard.tsx
// ─────────────────────────────────────────────────────────────
export function OfferCard() {
  const { offer } = usePipelineStore()

  if (!offer) {
    return <p className="text-xs font-mono text-gray-400 italic">Offer architecture will generate here...</p>
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-brand-200 bg-brand-50/40 overflow-hidden"
    >
      <div className="flex items-center justify-between px-4 py-3 bg-brand-50 border-b border-brand-200">
        <span className="text-sm font-medium text-brand-600">{offer.title}</span>
        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-brand-500 text-white">
          {offer.price_anchor}
        </span>
      </div>
      <div className="p-4 space-y-3">
        <p className="text-sm text-gray-600 italic border-l-2 border-brand-300 pl-3">
          {offer.hook}
        </p>
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-gray-400 mb-2">Core promise</div>
          <p className="text-xs text-gray-700">{offer.core_promise}</p>
        </div>
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-gray-400 mb-2">Modules</div>
          <div className="space-y-1.5">
            {offer.modules?.map((mod: string, i: number) => (
              <div key={i} className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-brand-100 border border-brand-200 text-brand-500 text-[10px] flex items-center justify-center flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span className="text-xs text-gray-700">{mod}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ─────────────────────────────────────────────────────────────
// ContentMap.tsx
// ─────────────────────────────────────────────────────────────
export function ContentMap() {
  const { contentMap } = usePipelineStore()

  if (!contentMap) return null

  const formats = [
    { key: 'twitter_thread',  label: 'Twitter/X Thread',    color: 'blue',   preview: contentMap.twitter_thread?.substring(0, 120) },
    { key: 'email_subject',   label: 'Email Newsletter',     color: 'teal',   preview: contentMap.email_subject },
    { key: 'linkedin_angle',  label: 'LinkedIn Article',     color: 'amber',  preview: contentMap.linkedin_angle?.substring(0, 120) },
  ]

  return (
    <div className="space-y-2">
      <div className="text-[10px] font-mono uppercase tracking-widest text-gray-400">Content repurposing map</div>
      {formats.map(f => (
        <motion.div
          key={f.key}
          initial={{ opacity: 0, x: -4 }}
          animate={{ opacity: 1, x: 0 }}
          className={clsx(
            'p-3 rounded-xl border cursor-pointer hover:opacity-90 transition-opacity',
            f.color === 'blue'  && 'bg-blue-50 border-blue-200',
            f.color === 'teal'  && 'bg-emerald-50 border-emerald-200',
            f.color === 'amber' && 'bg-amber-50 border-amber-200',
          )}
        >
          <div className={clsx(
            'text-xs font-medium mb-1',
            f.color === 'blue'  && 'text-blue-700',
            f.color === 'teal'  && 'text-emerald-700',
            f.color === 'amber' && 'text-amber-700',
          )}>
            {f.label}
          </div>
          <p className="text-xs text-gray-600 leading-relaxed">{f.preview}...</p>
        </motion.div>
      ))}

      {contentMap.short_form_clips?.length > 0 && (
        <div className="p-3 rounded-xl border border-purple-200 bg-purple-50">
          <div className="text-xs font-medium text-purple-700 mb-2">Short-form Clips ({contentMap.short_form_clips.length})</div>
          {contentMap.short_form_clips.map((clip: any, i: number) => (
            <div key={i} className="text-xs text-gray-600 mb-1">
              <span className="font-medium">{clip.title}</span> — {clip.hook?.substring(0, 60)}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// needed for clsx in this file
import clsx from 'clsx'

// Default exports
export default AgentGraph
