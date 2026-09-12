-- ====================================================================
-- CivicPulse API - Supabase Database Schema
-- Run this in your Supabase Project -> SQL Editor -> New Query -> Run
-- ====================================================================

-- 1. Create Users Table (for Web Dashboard Auth)
CREATE TABLE IF NOT EXISTS public.users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create API Keys Table
CREATE TABLE IF NOT EXISTS public.api_keys (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key_hash TEXT UNIQUE NOT NULL,
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    tier TEXT NOT NULL DEFAULT 'free',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    total_requests BIGINT DEFAULT 0,
    last_used_at TIMESTAMPTZ
);

-- 3. Create API Usage & Request Logs Table (for Stripe Request Inspector)
CREATE TABLE IF NOT EXISTS public.usage_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id TEXT,
    method TEXT DEFAULT 'GET',
    key_prefix TEXT,
    endpoint TEXT NOT NULL,
    city TEXT,
    query_params TEXT,
    status_code INTEGER NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create Indexes for High Performance
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON public.api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_email ON public.api_keys(email);
CREATE INDEX IF NOT EXISTS idx_usage_logs_timestamp ON public.usage_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_usage_logs_city ON public.usage_logs(city);
CREATE INDEX IF NOT EXISTS idx_usage_logs_status ON public.usage_logs(status_code);

-- 5. Enable Row Level Security (RLS) and Grant Access for publishable key
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow anon read users" ON public.users;
CREATE POLICY "Allow anon read users" ON public.users FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow anon insert users" ON public.users;
CREATE POLICY "Allow anon insert users" ON public.users FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS "Allow anon update users" ON public.users;
CREATE POLICY "Allow anon update users" ON public.users FOR UPDATE USING (true);

ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow anon read api_keys" ON public.api_keys;
CREATE POLICY "Allow anon read api_keys" ON public.api_keys FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow anon insert api_keys" ON public.api_keys;
CREATE POLICY "Allow anon insert api_keys" ON public.api_keys FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS "Allow anon update api_keys" ON public.api_keys;
CREATE POLICY "Allow anon update api_keys" ON public.api_keys FOR UPDATE USING (true);

ALTER TABLE public.usage_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow anon read usage_logs" ON public.usage_logs;
CREATE POLICY "Allow anon read usage_logs" ON public.usage_logs FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow anon insert usage_logs" ON public.usage_logs;
CREATE POLICY "Allow anon insert usage_logs" ON public.usage_logs FOR INSERT WITH CHECK (true);

-- 6. Seed Demo User Account
-- Default Demo: developer@civicpulse.dev / Password123!
INSERT INTO public.users (email, password_hash, name)
VALUES (
    'developer@civicpulse.dev',
    'scrypt:32768:8:1$uH3y5Qj9sN6q$29e9cb2b192e272bb0639d4e5f76906a58b87e2469d4d5e167cfcfceb4eb5b1c97a7da0eb3f124564c7da694ea5116df3341b5cf3c07658c148cf49c95350fa6',
    'Demo Developer'
) ON CONFLICT (email) DO NOTHING;

-- 7. Seed Initial Demo Keys
INSERT INTO public.api_keys (key_hash, key_prefix, name, email, tier)
VALUES 
    ('civic_demo_free_key_2026', 'civic_demo_free', 'Free Explorer Demo', 'developer@civicpulse.dev', 'free'),
    ('civic_demo_pro_key_2026', 'civic_demo_pro', 'Professional Developer Demo', 'developer@civicpulse.dev', 'developer'),
    ('civic_demo_enterprise_key_2026', 'civic_demo_ent', 'Enterprise Demo', 'enterprise@civicpulse.dev', 'enterprise')
ON CONFLICT (key_hash) DO NOTHING;

-- 8. Seed Sample Request Logs for Stripe Inspector
INSERT INTO public.usage_logs (request_id, method, key_prefix, endpoint, city, query_params, status_code, latency_ms)
VALUES 
    ('req_01HV789A', 'GET', 'civic_demo_free', '/api/v1/incidents', 'las_vegas', 'city=las_vegas&limit=10', 200, 14.2),
    ('req_01HV789B', 'GET', 'civic_demo_pro', '/api/v1/incidents', 'los_angeles', 'city=los_angeles&category=Property+Crime', 200, 18.6),
    ('req_01HV789C', 'GET', 'civic_demo_free', '/api/v1/permits', 'seattle', 'city=seattle&limit=5', 200, 22.4),
    ('req_01HV789D', 'GET', 'civic_demo_ent', '/api/v1/analytics/summary', NULL, '', 200, 31.8),
    ('req_01HV789E', 'GET', 'civic_demo_free', '/api/v1/incidents', 'phoenix', 'city=phoenix&limit=15', 200, 16.9)
ON CONFLICT DO NOTHING;
