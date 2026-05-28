-- ─────────────────────────────────────────────────────────────
-- CreatorLens — Supabase Migration
-- Run this in your Supabase SQL editor
-- ─────────────────────────────────────────────────────────────

-- Enable pgvector extension
create extension if not exists vector;

-- ── video_chunks table ────────────────────────────────────────
create table if not exists video_chunks (
  id          bigserial primary key,
  job_id      text        not null,
  chunk_id    text        not null unique,
  text        text        not null,
  start_time  float       not null default 0,
  end_time    float       not null default 0,
  speaker     text        not null default 'SPK_0',
  embedding   vector(1536) not null,
  created_at  timestamptz not null default now()
);

-- Index for job_id lookups
create index if not exists idx_chunks_job_id on video_chunks(job_id);

-- IVFFlat index for fast cosine similarity search
-- (tune lists = sqrt(row_count) in production)
create index if not exists idx_chunks_embedding
  on video_chunks
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- ── RPC function for semantic search ─────────────────────────
create or replace function match_video_chunks(
  query_embedding vector(1536),
  match_job_id    text,
  match_count     int default 5
)
returns table (
  chunk_id   text,
  text       text,
  start_time float,
  end_time   float,
  speaker    text,
  distance   float
)
language sql stable
as $$
  select
    chunk_id,
    text,
    start_time,
    end_time,
    speaker,
    embedding <=> query_embedding as distance
  from video_chunks
  where job_id = match_job_id
  order by embedding <=> query_embedding
  limit match_count;
$$;

-- ── Row Level Security ────────────────────────────────────────
alter table video_chunks enable row level security;

-- Service role can do everything (backend uses service key)
create policy "service_role_all" on video_chunks
  for all
  using (auth.role() = 'service_role');

-- ── Cleanup old jobs (run as cron via pg_cron or external) ───
create or replace function cleanup_old_jobs(older_than_hours int default 24)
returns void language sql as $$
  delete from video_chunks
  where created_at < now() - (older_than_hours || ' hours')::interval;
$$;
