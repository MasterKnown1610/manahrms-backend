# Local Exotel testing — use ngrok (not nginx)
#
# nginx  → reverse proxy only, NO public temp URL
# ngrok  → gives https://xxxx.ngrok-free.app → localhost:8000  ← what Exotel needs
#
# Install once:
#   1. Download from https://ngrok.com/download (Windows)
#   2. Unzip, put ngrok.exe somewhere on PATH (or use full path)
#   3. Sign up free at https://dashboard.ngrok.com and run:
#        ngrok config add-authtoken YOUR_TOKEN
#
# Every local test session:
#   Terminal 1:
#     uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
#
#   Terminal 2:
#     ngrok http 8000
#
#   Copy the Forwarding HTTPS URL, e.g. https://abc123.ngrok-free.app
#
#   In .env (local only):
#     APP_PUBLIC_URL=https://abc123.ngrok-free.app
#   Restart uvicorn after changing .env
#
#   In Exotel dashboard (for testing):
#     Voicebot URL:
#       https://abc123.ngrok-free.app/api/v1/exotel/call/stream-url?token=dhiora-exotel-webhook-2026
#     Passthru (async) URL:
#       https://abc123.ngrok-free.app/api/v1/exotel/call/complete?token=dhiora-exotel-webhook-2026
#
#   Call: 08047361154
#
# Live production again:
#   APP_PUBLIC_URL=https://api.manahrms.com
#   Exotel URLs back to api.manahrms.com/...
