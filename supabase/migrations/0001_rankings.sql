-- The Delta Duo — rankings storage.
-- Run this in the Supabase SQL editor (or `supabase db push`).
-- Uploaded sets override the baked-in boards on the site; each upload creates
-- a new set per format so history is preserved.

create table if not exists public.ranking_sets (
  id uuid primary key default gen_random_uuid(),
  scope text not null check (scope in ('ppr', 'halfppr', 'superflex')),
  filename text,
  created_at timestamptz not null default now()
);

create table if not exists public.rankings (
  id bigint generated always as identity primary key,
  set_id uuid not null references public.ranking_sets (id) on delete cascade,
  rank int not null,
  player text not null,
  pos text,
  pos_rank text,
  team text,
  bye int,
  tier text,
  note text
);

create index if not exists rankings_set_id_rank_idx on public.rankings (set_id, rank);
create index if not exists ranking_sets_scope_created_idx on public.ranking_sets (scope, created_at desc);

-- Anyone may read rankings; writes only happen through the service role
-- (the site's server route), which bypasses RLS. No insert/update/delete
-- policies are defined on purpose.
alter table public.ranking_sets enable row level security;
alter table public.rankings enable row level security;

create policy "public read ranking_sets" on public.ranking_sets for select using (true);
create policy "public read rankings" on public.rankings for select using (true);
