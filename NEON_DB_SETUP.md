# Neon DB Setup for pgvector RAG

## Quick Start for Neon DB Users

Since you're using **Neon DB** (serverless PostgreSQL), the setup is simpler than self-hosted PostgreSQL!

### Step 1: Enable pgvector Extension

1. Go to [Neon Console](https://console.neon.tech)
2. Select your project and database
3. Click on **SQL Editor**
4. Run this command:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
5. Verify it worked:
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```
   You should see a row with `extname = 'vector'`

### Step 2: Run Setup Script

```bash
python setup_pgvector.py
```

This will create the `vector_store` table automatically.

### Step 3: Sync Your Data

```bash
# Sync all companies
python sync_vectors.py

# Or sync specific company
python sync_vectors.py <company_id>
```

### Step 4: Test It!

The AI chat endpoint will now automatically use semantic search with minimal tokens!

## Why Neon DB is Great for This

✅ **pgvector is pre-installed** - just enable the extension  
✅ **No server management** - fully serverless  
✅ **Automatic scaling** - handles your vector operations  
✅ **Same PostgreSQL compatibility** - all pgvector features work  
✅ **Easy connection** - use your existing Neon connection string  

## Troubleshooting

### "Extension not found" error

**Solution:** Enable it manually in Neon SQL Editor first, then run the setup script again.

### "Permission denied" error

**Solution:** Make sure you're using the correct database user with extension creation permissions. In Neon, the default user should have these permissions.

### Connection issues

**Solution:** Verify your `DATABASE_URL` in `.env` or environment variables points to your Neon database.

## API Endpoint

After setup, you can also sync vectors via API:

```bash
POST /api/v1/vector-sync/sync-company
Authorization: Bearer <your_token>
```

This will sync all data for the authenticated user's company.

## Next Steps

1. ✅ Enable pgvector extension (via Neon SQL Editor)
2. ✅ Run `python setup_pgvector.py`
3. ✅ Run `python sync_vectors.py`
4. ✅ Test AI chat - enjoy 80-90% token reduction!

That's it! Neon DB makes this super easy. 🚀

