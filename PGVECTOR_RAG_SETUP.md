# pgvector RAG Implementation Guide

## Overview

This implementation replaces the previous token-heavy RAG approach with an efficient pgvector-based semantic search system. Instead of loading ALL company data into every query (which consumed thousands of tokens), the new system:

1. **Stores embeddings** of company data (employees, projects, tasks, departments) in PostgreSQL using pgvector
2. **Retrieves only relevant chunks** based on semantic similarity to the user's question
3. **Dramatically reduces token consumption** by sending only 5-10 relevant chunks instead of all data

## Token Savings

### Before (Old Implementation)

- **Every query**: Loaded ALL employees (up to 50), ALL projects (up to 20), ALL tasks (up to 50), ALL departments
- **Typical context size**: 2000-5000 tokens per query
- **Cost**: High, especially with frequent queries

### After (pgvector Implementation)

- **Every query**: Only retrieves top 10 most relevant chunks based on semantic similarity
- **Typical context size**: 200-500 tokens per query
- **Cost**: 80-90% reduction in token consumption

## Setup Instructions

### 1. Enable pgvector Extension

**For Neon DB (Serverless PostgreSQL):**

Neon DB supports pgvector out of the box! You just need to enable it:

1. Go to your [Neon Dashboard](https://console.neon.tech)
2. Select your project and database
3. Open the **SQL Editor**
4. Run this command:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
5. Verify it's enabled:
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

**For Self-Hosted PostgreSQL:**

**Ubuntu/Debian:**

```bash
sudo apt-get install postgresql-14-pgvector  # Adjust version as needed
```

**macOS (Homebrew):**

```bash
brew install pgvector
```

**From Source:**

```bash
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

Then enable it:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

The `pgvector==0.2.4` package has been added to requirements.txt.

### 3. Setup Database

**For Neon DB users:** Make sure you've enabled the pgvector extension via the SQL Editor first (see step 1).

Run the setup script to create the vector_store table:

```bash
python setup_pgvector.py
```

This will:

- Verify the `vector` extension is enabled (or try to enable it)
- Create the `vector_store` table with proper indexes
- Verify the setup

**Note for Neon DB:** If the script can't enable the extension automatically, enable it manually via the Neon SQL Editor, then run the script again.

### 4. Sync Company Data to Vector Store

After setup, you need to populate embeddings for your company data:

**Option A: Using the script**

```bash
# Sync all companies
python sync_vectors.py

# Sync specific company
python sync_vectors.py <company_id>
```

**Option B: Using the API endpoint**

```bash
POST /api/v1/vector-sync/sync-company
Authorization: Bearer <token>
```

## Architecture

### Components

1. **VectorStore Model** (`app/api/v1/models/vector_store_model.py`)

   - Stores embeddings with metadata
   - Uses pgvector's `Vector` type (1536 dimensions for OpenAI text-embedding-3-small)

2. **EmbeddingService** (`app/api/v1/services/embedding_service.py`)

   - Generates embeddings using OpenAI's text-embedding-3-small model
   - Formats content for embedding (employees, projects, tasks, etc.)

3. **VectorSyncService** (`app/api/v1/services/vector_sync_service.py`)

   - Syncs company data to vector store
   - Updates embeddings when data changes
   - Can be called after CRUD operations

4. **AIChatService** (Refactored) (`app/api/v1/services/ai_chat_service.py`)
   - Uses semantic search instead of loading all data
   - Retrieves top 10 most relevant chunks
   - Builds minimal context for LLM

### How It Works

1. **Data Ingestion**:

   - When employees/projects/tasks are created/updated, sync to vector store
   - Each record gets an embedding generated from its text representation
   - Embeddings are stored in PostgreSQL with pgvector

2. **Query Processing**:

   - User asks a question
   - Question is converted to an embedding
   - Semantic search finds top 10 most similar chunks using cosine distance
   - Only relevant chunks are sent to LLM (not all data)
   - LLM generates response based on minimal, relevant context

3. **Similarity Search**:
   ```sql
   SELECT content_text, metadata,
          1 - (embedding <=> query_embedding) AS similarity
   FROM vector_store
   WHERE company_id = ?
   ORDER BY embedding <=> query_embedding
   LIMIT 10
   ```

## Usage

### Automatic Sync

You can integrate vector sync into your CRUD operations. For example, after creating/updating an employee:

```python
from app.api.v1.services.vector_sync_service import VectorSyncService

# After creating/updating employee
sync_service = VectorSyncService()
sync_service.sync_employee(db, employee_id)
```

### Manual Sync

Use the sync endpoint or script when:

- Bulk data imports
- After major data updates
- Periodic maintenance

### Querying

The AI chat endpoint works the same way, but now uses semantic search:

```bash
POST /api/v1/ai-chat/ask
{
  "question": "Who is working on the marketing project?",
  "conversation_history": null
}
```

The system will:

1. Generate embedding for the question
2. Find relevant employees/projects/tasks
3. Send only relevant data to LLM
4. Return accurate answer with minimal tokens

## Maintenance

### Re-syncing Data

If embeddings become stale or you need to refresh:

```bash
python sync_vectors.py
```

Or use the API endpoint for a specific company.

### Monitoring

Check vector store size:

```sql
SELECT content_type, COUNT(*)
FROM vector_store
WHERE company_id = ?
GROUP BY content_type;
```

### Performance

- **Embedding Generation**: ~100ms per item (OpenAI API)
- **Similarity Search**: <10ms for top 10 results (with proper indexes)
- **Total Query Time**: ~200-300ms (including embedding + search + LLM)

## Troubleshooting

### pgvector Extension Not Found

**For Neon DB:**

1. Go to Neon Dashboard → SQL Editor
2. Run: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Verify: `SELECT * FROM pg_extension WHERE extname = 'vector';`
4. Re-run the setup script

**For Self-Hosted PostgreSQL:**

1. Ensure pgvector is installed in PostgreSQL
2. Check PostgreSQL version compatibility
3. Verify extension is enabled: `CREATE EXTENSION vector;`

### No Results from Semantic Search

If queries return no relevant chunks:

1. Ensure vectors are synced: `python sync_vectors.py`
2. Check if company has data in vector_store table
3. Verify embeddings were generated successfully

### High Token Usage Still

If you're still seeing high token usage:

1. Check if old implementation is still being used
2. Verify vector_store table has data
3. Check similarity threshold (currently top 10, can be adjusted)

## Benefits

✅ **80-90% token reduction** - Only relevant data sent to LLM
✅ **Better accuracy** - Semantic search finds truly relevant information
✅ **Scalable** - Works efficiently even with thousands of records
✅ **Cost-effective** - Significant reduction in OpenAI API costs
✅ **Fast** - pgvector similarity search is very fast
✅ **Maintainable** - Embeddings stored in same database as data

## Next Steps

1. **Enable pgvector extension:**

   - **Neon DB**: Use SQL Editor in Neon dashboard to run `CREATE EXTENSION vector;`
   - **Self-hosted**: Install and enable pgvector (see step 1 above)

2. **Run setup script:**

   ```bash
   python setup_pgvector.py
   ```

3. **Sync your existing data:**

   ```bash
   python sync_vectors.py
   ```

4. **Test the AI chat endpoint** - it will automatically use semantic search

5. **Monitor token usage** to see the 80-90% reduction!

## Neon DB Specific Notes

✅ **pgvector is fully supported** in Neon DB  
✅ **No installation needed** - just enable the extension via SQL Editor  
✅ **Works seamlessly** with your existing Neon connection string  
✅ **Same performance** as regular PostgreSQL for vector operations
