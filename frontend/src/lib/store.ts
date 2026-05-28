import { create } from 'zustand'

export type StageStatus = 'idle' | 'active' | 'done' | 'error'

export interface StageState {
  status: StageStatus
  progress: number
  message: string
  data: Record<string, any> | null
}

export interface AgentFire {
  name: string
  status: 'idle' | 'firing' | 'done'
}

export interface PipelineStore {
  // Input
  videoUrl: string
  setVideoUrl: (url: string) => void

  // Job
  jobId: string | null
  isRunning: boolean

  // Stages
  stages: Record<string, StageState>

  // Agents
  agents: AgentFire[]

  // Results
  transcript: any[]
  chunks: any[]
  agentResults: any[]
  offer: any | null
  contentMap: any | null

  // Metrics
  totalTokens: number
  totalCostUsd: number
  totalLatencyMs: number
  monetizationScore: number

  // Logs
  logs: Array<{ time: string; level: string; message: string }>

  // Search
  searchQuery: string
  searchResults: any[]
  searchLatency: number
  injectionDetected: boolean
  isSearching: boolean
  setSearchQuery: (q: string) => void

  // Actions
  startPipeline: () => void
  handleEvent: (event: any) => void
  runSearch: (jobId: string, query: string) => Promise<void>
  reset: () => void
}

const INITIAL_STAGES: Record<string, StageState> = {
  ingestion:  { status: 'idle', progress: 0, message: 'Waiting...', data: null },
  agents:     { status: 'idle', progress: 0, message: 'Waiting...', data: null },
  embedding:  { status: 'idle', progress: 0, message: 'Waiting...', data: null },
  repurpose:  { status: 'idle', progress: 0, message: 'Waiting...', data: null },
}

const INITIAL_AGENTS: AgentFire[] = [
  { name: 'TopicModeler',         status: 'idle' },
  { name: 'SentimentAnalyzer',    status: 'idle' },
  { name: 'MonetizationDetector', status: 'idle' },
  { name: 'OfferArchitect',       status: 'idle' },
]

const addLog = (logs: any[], level: string, message: string) => {
  const time = new Date().toLocaleTimeString('en', { hour12: false })
  return [...logs, { time, level, message }].slice(-100) // keep last 100
}

export const usePipelineStore = create<PipelineStore>((set, get) => ({
  videoUrl: '',
  setVideoUrl: (url) => set({ videoUrl: url }),

  jobId: null,
  isRunning: false,

  stages: INITIAL_STAGES,
  agents: INITIAL_AGENTS,

  transcript: [],
  chunks: [],
  agentResults: [],
  offer: null,
  contentMap: null,

  totalTokens: 0,
  totalCostUsd: 0,
  totalLatencyMs: 0,
  monetizationScore: 0,

  logs: [],

  searchQuery: '',
  searchResults: [],
  searchLatency: 0,
  injectionDetected: false,
  isSearching: false,
  setSearchQuery: (q) => set({ searchQuery: q }),

  startPipeline: () => {
    set({
      isRunning: true,
      jobId: null,
      stages: INITIAL_STAGES,
      agents: INITIAL_AGENTS,
      transcript: [],
      chunks: [],
      agentResults: [],
      offer: null,
      contentMap: null,
      totalTokens: 0,
      totalCostUsd: 0,
      totalLatencyMs: 0,
      monetizationScore: 0,
      logs: [],
      searchResults: [],
    })
  },

  handleEvent: (event) => {
    const { stages, agents, logs } = get()

    switch (event.event) {
      case 'job_created':
        set({
          jobId: event.data?.job_id,
          logs: addLog(logs, 'info', `Job ${event.data?.job_id} created`),
        })
        break

      case 'stage_start': {
        const stage = event.stage
        if (!stage) break
        set({
          stages: {
            ...stages,
            [stage]: { status: 'active', progress: event.progress || 0, message: event.message || '', data: null },
          },
          logs: addLog(get().logs, 'info', `[${stage}] ${event.message}`),
        })
        break
      }

      case 'stage_done': {
        const stage = event.stage
        if (!stage) break
        set({
          stages: {
            ...stages,
            [stage]: { status: 'done', progress: event.progress || 100, message: event.message || '', data: event.data || null },
          },
          logs: addLog(get().logs, 'info', `✓ [${stage}] ${event.message}`),
          ...(stage === 'ingestion' && event.data ? {
            transcript: event.data.transcript || [],
          } : {}),
          ...(stage === 'agents' && event.data ? {
            agentResults: event.data.agent_results || [],
          } : {}),
          ...(stage === 'embedding' && event.data ? {
            chunks: event.data.chunks_preview || [],
          } : {}),
          ...(stage === 'repurpose' && event.data ? {
            contentMap: event.data.content_map || null,
          } : {}),
        })
        break
      }

      case 'agent_update': {
        const agentName = event.data?.agent
        const status = event.data?.status
        if (!agentName) break
        set({
          agents: agents.map(a =>
            a.name === agentName ? { ...a, status: status === 'firing' ? 'firing' : 'done' } : a
          ),
        })
        break
      }

      case 'complete':
        set({
          isRunning: false,
          totalTokens: event.data?.total_tokens || 0,
          totalCostUsd: event.data?.total_cost_usd || 0,
          totalLatencyMs: event.data?.total_latency_ms || 0,
          monetizationScore: event.data?.monetization_score || 0,
          offer: event.data?.result?.offer || null,
          logs: addLog(get().logs, 'info', `Pipeline complete ✓`),
        })
        break

      case 'error':
        set({
          isRunning: false,
          logs: addLog(get().logs, 'error', `ERROR: ${event.message}`),
        })
        break
    }
  },

  runSearch: async (jobId, query) => {
    const { semanticSearch } = await import('@/lib/api')
    set({ isSearching: true, injectionDetected: false, searchResults: [] })

    try {
      const res = await semanticSearch({ job_id: jobId, query, top_k: 5 })
      set({
        searchResults: res.results,
        searchLatency: res.latency_ms,
        injectionDetected: res.injection_detected,
        isSearching: false,
        logs: addLog(get().logs, 'info',
          res.injection_detected
            ? `[SECURITY] Injection blocked: "${query.substring(0, 40)}"`
            : `[search] ${res.results.length} results for "${query.substring(0, 40)}"`
        ),
      })
    } catch (err: any) {
      set({ isSearching: false, logs: addLog(get().logs, 'error', `Search error: ${err.message}`) })
    }
  },

  reset: () => set({
    isRunning: false, jobId: null, stages: INITIAL_STAGES, agents: INITIAL_AGENTS,
    transcript: [], chunks: [], agentResults: [], offer: null, contentMap: null,
    totalTokens: 0, totalCostUsd: 0, totalLatencyMs: 0, monetizationScore: 0,
    logs: [], searchResults: [],
  }),
}))
