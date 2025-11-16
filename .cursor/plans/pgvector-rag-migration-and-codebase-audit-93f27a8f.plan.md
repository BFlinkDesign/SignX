<!-- 93f27a8f-9dec-401c-a25d-95e979019059 c6cd1d71-1bea-49e4-bfde-ffe13cf6bb4e -->
# pgvector RAG Migration & Codebase Audit Plan

## Phase 1: pgvector RAG Implementation (Steps 1-4)

### Step 1: Database Schema Setup

**File**: `services/api/alembic/versions/XXX_add_corpus_chunks.py`

Create Alembic migration to add corpus storage:

- Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
- Create `corpus_chunks` table with:
- `id` (UUID primary key)
- `file_path` (TEXT) - Original source file path
- `category` (TEXT) - cat_scale, engineering, estimating, etc.
- `chunk_text` (TEXT) - Text content (500-1000 tokens)
- `chunk_index` (INTEGER) - Position in file
- `embedding` (VECTOR(768)) - Gemini embedding-001 dimension
- `metadata` (JSONB) - File metadata, upload date, etc.
- `created_at` (TIMESTAMPTZ)
- Create IVFFlat index for cosine similarity search
- Add indexes on `category`, `file_path` for filtering

**Reference**: `services/api/migrations/README.md` shows pgvector support pattern

### Step 2: Ingestion Pipeline

**File**: `scripts/ingest_corpus_to_pgvector.py`

Build HTML → chunks → embeddings → PostgreSQL pipeline:

- Read HTML files from `Desktop/Gemini_Eagle_Knowledge_Base/`
- Chunk text using tiktoken or simple token counting (~500 tokens/chunk)
- Generate embeddings using Gemini `embedding-001` model (free tier)
- Batch insert chunks + embeddings into PostgreSQL
- Track progress and handle errors gracefully
- Support incremental updates (skip already-ingested files)

**Dependencies**:

- `google-generativeai` (already installed)
- `psycopg2` or `asyncpg` for PostgreSQL
- `tiktoken` for token counting

**Reference**: Reuse chunking logic from `setup_gemini_corpus.py`

### Step 3: Update RAG Service

**File**: `modules/rag/service.py`

Replace Gemini File API with pgvector queries:

- Remove `genai.upload_file()` and `genai.list_files()` calls
- Add PostgreSQL connection using existing `get_db()` pattern
- Implement `_query_pgvector()` method:
- Generate query embedding using Gemini embeddings API
- Query `corpus_chunks` table with cosine similarity
- Filter by category if specified
- Return top N chunks (default 15)
- Update `query()` method to:
- Get chunks from pgvector instead of file URIs
- Pass chunk text directly to Gemini (not file URIs)
- Maintain same response format for backward compatibility
- Keep retry logic and error handling

**Reference**: `services/api/src/apex/api/db.py` shows database connection pattern

### Step 4: Update Tests & Validation

**Files**:

- `scripts/test_rag_accuracy.py`
- `scripts/test_quote_generation_simple.py`

Update test scripts:

- Remove file upload steps
- Test pgvector retrieval directly
- Verify accuracy maintained (target: 91%+)
- Measure query performance (target: <100ms retrieval)
- Update test documentation

**New test**: `scripts/test_pgvector_rag.py` - Dedicated pgvector tests

---

## Phase 2: Codebase Audit for Technical Debt

### Audit Categories

#### A. TODO/FIXME Comments (587 found across 170 files)

**Priority**: High-impact TODOs in production code

**Key files to review**:

- `modules/quoting/__init__.py` (lines 207, 296, 433, 493, 523)
- Line 296: SignX-Intel ML integration missing
- Line 433: PDF generation not implemented
- `modules/rag/service.py` (line 297)
- Citation parsing incomplete
- `modules/workflow/__init__.py` (line 111)
- Email monitoring not implemented

**Action**: Categorize by:

- Critical (blocks production features)
- Important (missing functionality)
- Nice-to-have (optimizations)

#### B. Hardcoded Values & Configuration

**Search for**:

- Hardcoded API keys (security risk)
- Magic numbers without constants
- Hardcoded file paths
- Environment-specific values

**Files to check**:

- `modules/rag/service.py` - API key handling
- `scripts/*.py` - Hardcoded paths
- `modules/quoting/__init__.py` - Base cost dictionary (lines 300-306)

#### C. Insufficient Error Handling

**Look for**:

- Bare `except:` clauses
- Missing try/except blocks
- Unhandled API failures
- No retry logic where needed

**Files to review**:

- `modules/rag/service.py` - API error handling
- `modules/quoting/__init__.py` - RAG query failures
- All API route handlers

#### D. Workarounds & Hacks

**Search for**:

- Comments like "HACK", "WORKAROUND", "TEMP"
- Complex workarounds that should be refactored
- Band-aid solutions

#### E. Missing Implementations

**Check**:

- Empty function bodies with `pass`
- Functions that return placeholder data
- Stub implementations

**Key areas**:

- `modules/quoting/_estimate_costs()` - Uses hardcoded base costs
- `modules/workflow/` - Email monitoring stubbed
- PDF generation endpoints

#### F. Performance Issues

**Look for**:

- N+1 query patterns
- Missing database indexes
- Inefficient algorithms
- No caching where beneficial

#### G. Security Concerns

**Check**:

- Exposed API keys
- Missing input validation
- SQL injection risks
- Missing authentication checks

---

## Implementation Order

1. **Step 1**: Database schema (1-2 hours)
2. **Step 2**: Ingestion pipeline (3-4 hours)
3. **Step 3**: RAG service update (2-3 hours)
4. **Step 4**: Test updates (1-2 hours)
5. **Phase 2**: Codebase audit (4-6 hours)

**Total estimated time**: 12-18 hours

---

## Success Criteria

### pgvector Migration

- [ ] All 2,190 files ingested into pgvector
- [ ] RAG queries work without file expiration
- [ ] Accuracy maintained (91%+)
- [ ] Query performance <100ms retrieval
- [ ] Tests pass

### Codebase Audit

- [ ] All critical TODOs documented
- [ ] Security issues identified
- [ ] Performance bottlenecks cataloged
- [ ] Refactoring priorities established
- [ ] Action plan created for fixes

---

## Files to Create/Modify

### New Files

- `services/api/alembic/versions/XXX_add_corpus_chunks.py`
- `scripts/ingest_corpus_to_pgvector.py`
- `scripts/test_pgvector_rag.py`
- `docs/TECHNICAL_DEBT_AUDIT.md`

### Modified Files

- `modules/rag/service.py` - Replace Gemini File API with pgvector
- `modules/rag/__init__.py` - Update if needed
- `scripts/test_rag_accuracy.py` - Update for pgvector
- `scripts/test_quote_generation_simple.py` - Update tests
- `env.example` - Add embedding model config if needed

---

## Questions to Resolve

1. **Embedding Model**: Use Gemini `embedding-001` (free) or another model?
2. **Migration Strategy**: Replace Gemini File API completely or keep as fallback?
3. **Chunk Size**: 500 tokens (current) or adjust based on testing?
4. **Audit Scope**: Focus on production code (`modules/`, `services/api/`) or include scripts/docs?

### To-dos

- [ ] Create Alembic migration for corpus_chunks table with pgvector extension
- [ ] Build ingestion pipeline: HTML → chunks → embeddings → PostgreSQL
- [ ] Update RAG service to query pgvector instead of Gemini File API
- [ ] Update test scripts and validate accuracy/performance
- [ ] Audit TODO/FIXME comments (587 found) - categorize by priority
- [ ] Identify hardcoded values, missing error handling, and workarounds
- [ ] Document security concerns and performance bottlenecks
- [ ] Create technical debt report with prioritized action plan