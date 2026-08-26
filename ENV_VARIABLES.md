# Environment Variables Configuration

This document describes all environment variables that can be set in your `.env` file.

## Quick Start

1. Create a `.env` file in the root directory
2. Copy the variables below that you need
3. Update the values with your actual configuration
4. **Never commit `.env` to version control!**

---

## Required Variables (for basic functionality)

### Database Configuration

You can configure the database in two ways:

**Option 1: Individual settings (default)**
```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=123456
DATABASE_NAME=HRMS
```

**Option 2: Full connection URL (takes precedence)**
```env
DATABASE_URL=postgresql://postgres:123456@localhost:5432/HRMS
```

### JWT Authentication

```env
# IMPORTANT: Change this in production!
# Generate a secure key with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-secret-key-change-in-production-09876543210
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=720
```

---

## Optional Variables

### API Settings

```env
API_V1_PREFIX=/api/v1
PROJECT_NAME=HRMS Backend
```

### OpenAI (for AI Chatbot feature)

```env
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo

# Optional voice (STT/TTS) — same OPENAI_API_KEY; defaults shown
# OPENAI_WHISPER_MODEL=whisper-1
# OPENAI_TTS_MODEL=tts-1
# OPENAI_TTS_VOICE=alloy
# OPENAI_TTS_FORMAT=mp3
# MAX_VOICE_AUDIO_SIZE=26214400
```

**Note:** If `OPENAI_API_KEY` is not set, AI chatbot and voice (`/ai-chat/transcribe`, `/ai-chat/speak`) features will be disabled.

### Exotel inbound voice agent (Dhiora → leads)

Used by `/api/v1/exotel/call/*` for inbound calls on your ExoPhone (default `08047361154`).

```env
# Required for voice agent + lead creation
OPENAI_API_KEY=your-openai-api-key-here
EXOTEL_DEFAULT_COMPANY_ID=12
APP_PUBLIC_URL=https://your-public-domain.com

# Recommended — protects webhooks
EXOTEL_WEBHOOK_TOKEN=your-random-webhook-secret

# Optional Exotel API credentials (for future outbound/API use)
# EXOTEL_API_KEY=
# EXOTEL_API_TOKEN=
# EXOTEL_ACCOUNT_SID=
# EXOTEL_SUBDOMAIN=api.in.exotel.com
# EXOTEL_INBOUND_NUMBER=08047361154
# EXOTEL_OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview-2024-12-17

# Optional — override Dhiora knowledge for the voice agent
# DHIORA_KNOWLEDGE=Custom product description and FAQs...
```

**Exotel flow setup:** Voicebot → `GET /api/v1/exotel/call/stream-url` → Passthru (async) → `GET /api/v1/exotel/call/complete`

See `GET /api/v1/exotel/call/config` for generated URLs after deploy.

### File Upload Settings

```env
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760  # 10MB in bytes
```

### AWS S3 (for cloud file storage)

```env
USE_S3=false
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-s3-bucket-name

# Optional: For S3-compatible services (e.g., DigitalOcean Spaces)
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
```

**Note:** Set `USE_S3=true` to enable S3 storage. If `false` or not set, files are stored locally.

### Redis (for WebSocket Pub/Sub)

**Option 1: Full URL**
```env
REDIS_URL=redis://localhost:6379/0
# With password: REDIS_URL=redis://:password@localhost:6379/0
```

**Option 2: Individual settings**
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

**Note:** Redis is optional. If not configured, WebSocket features may have limited functionality.

### Razorpay Payment Gateway

```env
RAZORPAY_KEY_ID=your-razorpay-key-id
RAZORPAY_KEY_SECRET=your-razorpay-key-secret
RAZORPAY_WEBHOOK_SECRET=your-razorpay-webhook-secret
```

**Note:** If not set, payment features will be disabled (you'll see a warning in logs).

---

## Example .env File

Here's a minimal `.env` file for local development:

```env
# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=your-db-password
DATABASE_NAME=HRMS

# Security
SECRET_KEY=generate-a-secure-random-key-here

# Optional: OpenAI for AI features
# OPENAI_API_KEY=sk-...

# Optional: Razorpay for payments
# RAZORPAY_KEY_ID=rzp_...
# RAZORPAY_KEY_SECRET=...
# RAZORPAY_WEBHOOK_SECRET=...
```

---

## Production Checklist

- [ ] Set a strong, random `SECRET_KEY`
- [ ] Use a secure database password
- [ ] Configure production database connection
- [ ] Set up S3 or ensure local storage is properly secured
- [ ] Configure Redis if using WebSocket features
- [ ] Set up Razorpay credentials if using payment features
- [ ] Ensure `.env` is in `.gitignore` and never committed

---

## Default Values

All variables have default values defined in `app/core/config.py`. If a variable is not set in `.env`, the default will be used. Check the config file for specific defaults.

