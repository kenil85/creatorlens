-- CreatorLens — Supabase Migration
-- Run this in your Supabase SQL editor

-- Enable pgvector
create extension if not exists vector;

-- video_chunks table
-- NOTE: using 384 dims for sentence-transformers/all-MiniLM-L6-v2
create table if not exists video_chunks (
  id          bigserial primary key,
  job_id      text         not null,
  chunk_id    text         not null unique,
  text        text         not null,
  start_time  float        not null default 0,
  end_time    float        not null default 0,
  speaker     text         not null default 'SPK_0',
  embedding   vector(384)  not null,
  created_at  timestamptz  not null default now()
);

-- Indexes
create index if not exists idx_chunks_job_id
  on video_chunks(job_id);

create index if not exists idx_chunks_embedding
  on video_chunks
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 50);

-- Row Level Security
alter table video_chunks enable row level security;

create policy "service_role_all" on video_chunks
  for all
  using (auth.role() = 'service_role');

-- Cleanup old jobs
create or replace function cleanup_old_jobs(older_than_hours int default 24)
returns void language sql as $$
  delete from video_chunks
  where created_at < now() - (older_than_hours || ' hours')::interval;
$$;
