# Render Deployment Guide

## Issue: Rust/Maturin Build Error

If you're getting a `maturin` or Rust compilation error during deployment, it's because some Python packages (like `pydantic-core`) are written in Rust and need to be compiled.

## Solutions

### Solution 1: Use Pre-built Wheels (Recommended)

The `render.yaml` file is configured to prefer pre-built wheels. If this still fails:

1. **Update Python version** in Render dashboard to **3.11.0** or **3.12.0**
2. **Set Build Command** in Render dashboard:
   ```bash
   pip install --upgrade pip setuptools wheel && pip install --prefer-binary -r requirements.txt
   ```

### Solution 2: Use Python 3.11+ (Best Compatibility)

1. Go to Render Dashboard → Your Service → Settings
2. Set **Python Version** to `3.11.0` or `3.12.0`
3. These versions have better wheel support for Rust-based packages

### Solution 3: Alternative Requirements (If Still Failing)

If the build still fails, you can try using older versions with better wheel support:

```txt
# Alternative requirements.txt (if needed)
pydantic==2.5.3
pydantic-core==2.14.5  # Explicitly pin pydantic-core with wheel
```

### Solution 4: Manual Build Configuration

In Render Dashboard:

1. **Build Command:**

   ```bash
   pip install --upgrade pip setuptools wheel && pip install --prefer-binary --no-cache-dir -r requirements.txt
   ```

2. **Start Command:**

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

3. **Environment Variables:**

   - `DATABASE_URL`: Your PostgreSQL connection string (REQUIRED)
   - `SECRET_KEY`: Optional - defaults to a placeholder if not set (should be changed in production)
   - `PYTHON_VERSION`: Set automatically by Render (3.11.0 from render.yaml)

   **Note:** Your `.env` file only needs `DATABASE_URL`. Other variables have defaults in `app/core/config.py`:

   - `SECRET_KEY`: Has a default value (change in production!)
   - `DATABASE_HOST`, `DATABASE_PORT`, etc.: Have defaults (only needed if not using `DATABASE_URL`)

### Solution 5: Use Docker (Advanced)

If all else fails, you can use Docker deployment:

1. Create a `Dockerfile`:

   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   RUN pip install --upgrade pip setuptools wheel
   COPY requirements.txt .
   RUN pip install --prefer-binary -r requirements.txt

   COPY . .

   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. Deploy using Docker on Render

## Common Issues

### Issue: "Read-only file system"

- **Cause**: Render's build environment has restricted write access
- **Solution**: Use `--prefer-binary` flag to avoid compilation

### Issue: "maturin failed"

- **Cause**: Rust toolchain not available or package needs compilation
- **Solution**: Use Python 3.11+ and prefer binary wheels

### Issue: "pydantic-core not found"

- **Cause**: pydantic-core wheel not available for your Python version
- **Solution**: Use Python 3.11 or 3.12

## Environment Variables Setup

### Required in Render Dashboard:

- **`DATABASE_URL`**: Your PostgreSQL connection string
  - Format: `postgresql://user:password@host:port/database`
  - This is the ONLY required environment variable

### Optional (Have Defaults):

- **`SECRET_KEY`**: JWT secret key (defaults to placeholder - change in production!)
- **`DATABASE_HOST`**, **`DATABASE_PORT`**, etc.: Only needed if not using `DATABASE_URL`

### Your Current Setup:

Your `.env` file only needs:

```env
DATABASE_URL=postgresql://user:password@host:port/database
```

The app will use defaults from `app/core/config.py` for other settings.

## Verification

After deployment, check:

1. Service is running (green status)
2. Logs show: "Application startup complete"
3. Health check: `https://your-app.onrender.com/health`

## Need Help?

If deployment still fails:

1. Check Render build logs for specific error
2. Verify Python version matches `.python-version` file
3. Try deploying with Python 3.11 or 3.12
4. Contact Render support with build logs
