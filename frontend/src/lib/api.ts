const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface PipelineEvent {
  event: string
  stage?: string
  data?: Record<string, any>
  message?: string
  progress?: number
}

export interface SearchRequest {
  job_id: string
  query: string
  top_k?: number
}

export interface SearchResponse {
  query: string
  results: Array<{
    chunk_id: string
    text: string
    similarity_score: number
    start: number
    end: number
    speaker: string
  }>
  injection_detected: boolean
  latency_ms: number
}

/**
 * Run pipeline — returns an EventSource that streams SSE events.
 * Call onEvent for each event, onError on failure.
 */
export function runPipeline(
  videoUrl: string,
  onEvent: (event: PipelineEvent) => void,
  onError: (err: string) => void,
): () => void {
  let aborted = false

  const startStream = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/pipeline/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_url: videoUrl }),
      })

      if (!response.ok) {
        const err = await response.json()
        onError(err.detail || 'Pipeline failed to start')
        return
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        onError('No response stream available')
        return
      }

      let buffer = ''
      while (!aborted) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: PipelineEvent = JSON.parse(line.slice(6))
              onEvent(event)
            } catch {
              // ignore malformed events
            }
          }
        }
      }
    } catch (err: any) {
      if (!aborted) onError(err.message || 'Stream error')
    }
  }

  startStream()
  return () => { aborted = true }
}

/**
 * Semantic search over a completed job.
 */
export async function semanticSearch(req: SearchRequest): Promise<SearchResponse> {
  const res = await fetch(`${API_URL}/api/v1/search/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })

  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Search failed')
  }

  return res.json()
}

/**
 * Get full job result.
 */
export async function getJob(jobId: string) {
  const res = await fetch(`${API_URL}/api/v1/pipeline/job/${jobId}`)
  if (!res.ok) throw new Error('Job not found')
  return res.json()
}
