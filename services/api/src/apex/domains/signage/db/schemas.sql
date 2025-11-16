-- APEX Signage Engineering - Core Database Schemas
-- Pydantic-compatible; Postgres 15+ compatible

-- Core Project Management Tables
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE projects (
  project_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  account_id         UUID NOT NULL,
  name               TEXT NOT NULL,
  customer           TEXT,
  description        TEXT,
  site_name          TEXT,
  street             TEXT,
  status             TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','estimating','submitted','accepted','rejected')),
  created_by         TEXT NOT NULL,
  updated_by         TEXT NOT NULL,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE project_payloads (
  project_id   UUID PRIMARY KEY REFERENCES projects(project_id) ON DELETE CASCADE,
  module       TEXT NOT NULL CHECK (module IN ('signage.single_pole.direct_burial','signage.single_pole.base_plate','signage.two_pole.direct_burial')),
  config       JSONB NOT NULL,
  files        JSONB NOT NULL DEFAULT '[]'::JSONB,
  cost_snapshot JSONB NOT NULL DEFAULT '{}'::JSONB,
  version_sha  TEXT NOT NULL
);

CREATE TABLE project_events (
  id           BIGSERIAL PRIMARY KEY,
  project_id   UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  actor        TEXT NOT NULL,
  type         TEXT NOT NULL,
  data         JSONB NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Domain Engineering Tables

CREATE TABLE pole_sections (
  id            SERIAL PRIMARY KEY,
  type          TEXT NOT NULL,  -- 'HSS', 'Pipe', 'W'
  edition       TEXT NOT NULL,
  shape         TEXT NOT NULL,
  w_lbs_per_ft  FLOAT NOT NULL,
  a_in2         FLOAT NOT NULL,
  d_in          FLOAT,
  t_in          FLOAT,
  ix_in4        FLOAT NOT NULL,
  sx_in3        FLOAT NOT NULL,
  rx_in         FLOAT NOT NULL,
  zx_in3        FLOAT NOT NULL,
  fy_ksi        FLOAT DEFAULT 46.0,
  grade         TEXT DEFAULT 'A500B',
  UNIQUE(shape, edition)
);

CREATE TABLE calib_constants (
  name      TEXT PRIMARY KEY,
  value     FLOAT NOT NULL,
  source    TEXT NOT NULL,
  version   TEXT NOT NULL DEFAULT 'v1',
  notes     TEXT
);

CREATE TABLE config_pricing (
  code      TEXT PRIMARY KEY,
  label     TEXT NOT NULL,
  amount_usd FLOAT NOT NULL,
  version   TEXT NOT NULL DEFAULT 'v1',
  active    BOOLEAN DEFAULT TRUE
);

CREATE TABLE env_loads_cache (
  address_key TEXT PRIMARY KEY,
  loads       JSONB NOT NULL,
  api_version TEXT NOT NULL,
  fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at  TIMESTAMPTZ
);

-- Indexes for Performance
CREATE INDEX idx_projects_account_status ON projects(account_id, status);
CREATE INDEX idx_projects_search ON projects USING GIN (to_tsvector('english', name || ' ' || COALESCE(customer,'') || ' ' || COALESCE(description,'') || ' ' || COALESCE(site_name,'') || ' ' || COALESCE(street,'')));
CREATE INDEX idx_events_project_type ON project_events(project_id, type);
CREATE INDEX idx_events_created ON project_events(created_at DESC);

-- Pole Sections Indexes
CREATE INDEX idx_pole_sections_type_grade ON pole_sections(type, grade);
CREATE INDEX idx_pole_sections_sx ON pole_sections(sx_in3);

-- Constraint: Updated timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

