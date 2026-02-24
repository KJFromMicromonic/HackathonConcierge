-- Hackathon Concierge - Supabase Schema
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql

-- ============================================
-- TABLES
-- ============================================

-- User profiles (extends Supabase auth.users)
create table if not exists public.profiles (
  id uuid references auth.users on delete cascade primary key,
  display_name text,
  team_id uuid,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Teams (optional - for hackathon team management)
create table if not exists public.teams (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  project_name text,
  project_description text,
  track text,  -- e.g., "accessibility", "sustainability", "ai"
  created_at timestamptz default now()
);

-- Add foreign key for team_id after teams table exists
alter table public.profiles
  add constraint profiles_team_id_fkey
  foreign key (team_id) references public.teams(id) on delete set null;

-- User thread mappings (replaces in-memory/Redis session store)
create table if not exists public.user_threads (
  user_id uuid references auth.users on delete cascade primary key,
  thread_id text not null,  -- Backboard thread ID
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- User assistant mappings (per-user Backboard assistants)
create table if not exists public.user_assistants (
  user_id uuid references auth.users on delete cascade primary key,
  assistant_id text not null,  -- Backboard assistant ID
  created_at timestamptz default now()
);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
alter table public.profiles enable row level security;
alter table public.teams enable row level security;
alter table public.user_threads enable row level security;
alter table public.user_assistants enable row level security;

-- Profiles: Users can read/update their own profile
create policy "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- Teams: All authenticated users can view teams
create policy "Authenticated users can view teams"
  on public.teams for select
  to authenticated
  using (true);

-- User threads: Users can only access their own thread mapping
create policy "Users can view own thread"
  on public.user_threads for select
  using (auth.uid() = user_id);

create policy "Users can insert own thread"
  on public.user_threads for insert
  with check (auth.uid() = user_id);

create policy "Users can update own thread"
  on public.user_threads for update
  using (auth.uid() = user_id);

-- Service role can do everything (for backend)
create policy "Service role full access to profiles"
  on public.profiles for all
  to service_role
  using (true);

create policy "Service role full access to teams"
  on public.teams for all
  to service_role
  using (true);

create policy "Service role full access to user_threads"
  on public.user_threads for all
  to service_role
  using (true);

-- User assistants policies
create policy "Users can view own assistant"
  on public.user_assistants for select
  using (auth.uid() = user_id);

create policy "Service role full access to user_assistants"
  on public.user_assistants for all
  to service_role
  using (true);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Auto-create profile on user signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, new.raw_user_meta_data->>'display_name');
  return new;
end;
$$ language plpgsql security definer;

-- Trigger for new user signup
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Auto-update updated_at timestamp
create or replace function public.update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Triggers for updated_at
drop trigger if exists profiles_updated_at on public.profiles;
create trigger profiles_updated_at
  before update on public.profiles
  for each row execute procedure public.update_updated_at();

drop trigger if exists user_threads_updated_at on public.user_threads;
create trigger user_threads_updated_at
  before update on public.user_threads
  for each row execute procedure public.update_updated_at();

-- ============================================
-- INDEXES
-- ============================================

create index if not exists idx_profiles_team_id on public.profiles(team_id);
create index if not exists idx_user_threads_thread_id on public.user_threads(thread_id);

-- ============================================
-- DONE!
-- ============================================
-- Next steps:
-- 1. Go to Authentication > Providers and enable Email auth
-- 2. Copy your anon key and service_role key to .env:
--    SUPABASE_ANON_KEY=your_anon_key
--    SUPABASE_SERVICE_KEY=your_service_role_key
