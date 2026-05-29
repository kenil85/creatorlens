# CreatorLens — Video Intelligence Engine

> Built by **Kenil Sutariya** as an application for the Full Stack AI Engineer role at **CreatorJoy**.

A production-grade multi-agent pipeline that processes creator video content end-to-end:
transcription → LangGraph agent analysis → vector embedding → semantic search → monetization output.

---

## Architecture

```
YouTube URL
    │
    ▼
┌─────────────────────────────────────────┐
│  STAGE 1: INGESTION                     │
│  yt-dlp (audio-only) → Whisper API      │
│  → speaker diarization (pause-based)    │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  STAGE 2: LANGGRAPH AGENTS              │
│  StateGraph with 4 nodes:               │
│  TopicModeler → SentimentAnalyzer       │
│  → MonetizationDetector → OfferArchitect│
│  Shared state. Each agent enriches it.  │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  STAGE 3: VECTOR EMBEDDING              │
│  Sliding window chunking (size=3,       │
│  overlap=1) → text-embedding-3-small    │
│  → stored in Supabase pgvector          │
│  IVFFlat index, cosine similarity       │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  STAGE 4: SEMANTIC SEARCH + SECURITY    │
│  pgvector cosine search via RPC         │
│  Prompt injection detection (regex +    │
│  pattern matching on query input)       │
│  Input sanitization, XSS stripping      │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  STAGE 5: OUTPUT                        │
│  High-ticket offer architecture         │
│  Content repurposing map (Twitter,      │
│  email, LinkedIn, short-form clips)     │
│  All streamed via SSE to frontend       │
└─────────────────────────────────────────┘
```

## Stack

| Layer        | Technology                                   |
|--------------|----------------------------------------------|
| Backend      | Python 3.11, FastAPI, uvicorn                |
| AI Agents    | LangGraph 0.0.69, LangChain, GPT-4o-mini    |
| Transcription| OpenAI Whisper API + yt-dlp                  |
| Vector DB    | Supabase pgvector, text-embedding-3-small    |
| Security     | Token bucket rate limiter, injection defense |
| Streaming    | Server-Sent Events (SSE)                     |
| Frontend     | Next.js 14, TypeScript, Tailwind, Zustand    |
| Deployment   | Railway (backend), Vercel (frontend)         |

---

## Local Setup

### 1. Clone & install

```bash
git clone https://github.com/kenil0509/creatorlens
cd creatorlens
```

### 2. Backend

```bash
cd backend
cp .env.example .env
# Fill in your API keys in .env

pip install -r requirements.txt

# Run Supabase migration first (in Supabase SQL editor):
# Copy contents of migrations/001_init_pgvector.sql and run it

uvicorn app.main:app --reload
# API running at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000

npm install
npm run dev
# Frontend at http://localhost:3000
```

---

## Deploy

### Backend → Railway

```bash
cd backend
# Push to GitHub, connect repo to Railway
# Set env vars in Railway dashboard
# Railway auto-detects Dockerfile
```

### Frontend → Vercel

```bash
cd frontend
npx vercel
# Set NEXT_PUBLIC_API_URL=https://your-railway-app.railway.app
```

---

## API Reference

### `POST /api/v1/pipeline/run`
Start the pipeline. Returns SSE stream.

**Body:** `{ "video_url": "https://youtube.com/watch?v=..." }`

**Events streamed:**
- `job_created` — job ID assigned
- `stage_start` — stage beginning
- `stage_done` — stage complete with data
- `agent_update` — individual agent firing
- `complete` — full result
- `error` — failure with message

### `POST /api/v1/search/`
Semantic search over a completed job.

**Body:** `{ "job_id": "abc12345", "query": "what does the creator say about mindset?", "top_k": 5 }`

### `GET /api/v1/pipeline/job/{job_id}`
Get full result of a completed job.

---

## Security Notes

- **Rate limiting**: Token bucket per IP (configurable via `RATE_LIMIT_PER_MINUTE`)
- **Prompt injection defense**: 15 regex patterns on all search queries
- **Input sanitization**: XSS stripping, null byte removal, max length enforcement
- **URL validation**: Only YouTube and Vimeo allowed
- **File size limit**: 50MB max audio download via yt-dlp

---

## Author

**Kenil Sutariya**
- GitHub: [github.com/kenil0509](https://github.com/kenil0509)
- LinkedIn: [linkedin.com/in/kenil-sutariya-39b277213](https://linkedin.com/in/kenil-sutariya-39b277213)
