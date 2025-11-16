-- Row Level Security (RLS) Policies for Supabase
-- Run this SQL in your Supabase SQL editor or via migration

-- Enable RLS on core tables
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_payloads ENABLE ROW LEVEL SECURITY;

-- RLS Policies for projects table
CREATE POLICY "Users can view own projects"
    ON projects FOR SELECT
    USING (auth.uid()::text = created_by);

CREATE POLICY "Users can create projects"
    ON projects FOR INSERT
    WITH CHECK (auth.uid()::text = created_by);

CREATE POLICY "Users can update own projects"
    ON projects FOR UPDATE
    USING (auth.uid()::text = created_by)
    WITH CHECK (auth.uid()::text = updated_by);

CREATE POLICY "Users can delete own projects"
    ON projects FOR DELETE
    USING (auth.uid()::text = created_by);

-- RLS Policies for project_payloads table
CREATE POLICY "Users can view own project payloads"
    ON project_payloads FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.project_id = project_payloads.project_id
            AND projects.created_by = auth.uid()::text
        )
    );

CREATE POLICY "Users can create payloads for own projects"
    ON project_payloads FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.project_id = project_payloads.project_id
            AND projects.created_by = auth.uid()::text
        )
    );

-- Create user_accounts table for account/organization membership
CREATE TABLE IF NOT EXISTS user_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, account_id)
);

-- Enable RLS on user_accounts
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_accounts
CREATE POLICY "Users can view own accounts"
    ON user_accounts FOR SELECT
    USING (auth.uid() = user_id);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_user_accounts_user_id ON user_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_accounts_account_id ON user_accounts(account_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_by ON projects(created_by);
CREATE INDEX IF NOT EXISTS idx_projects_account_id ON projects(account_id);

