# 🤖 Fariborz Bot - Working Config (aug 5 2026 v4.1)

## Bot: @ShadowFariborz_bot
- Cloudflare Worker: fariborz
- Railway API: vigilant-perfection-production-b218

## Files
- `worker.js` → Cloudflare Worker
- `app.py` → Railway API

## Restore Steps
1. Deploy `worker.js` to Cloudflare Worker "fariborz"
2. KV binding: CHAT_HISTORY → a2a777fdf4e14a86b735726becf5b9ce
3. Deploy `app.py` to Railway
4. Variables: see below
5. pip install speech_recognition edge-tts

## Railway Variables
- TELEGRAM_BOT_TOKEN = (bot token)
- ADMIN_ID = 6236206739
- AI_API_KEY = (OpenRouter key)
- AI_BASE_URL = https://openrouter.ai/api/v1
- AI_MODEL = google/gemini-2.5-flash
- API_SECRET = fariborz-hermes-2024

## Cloudflare Variables
- TELEGRAM_BOT_TOKEN = (same)
- ADMIN_ID = 6236206739
- CHAT_HISTORY = KV namespace

## Features
- Chat + History
- Reply chain (5 levels)
- Photo analysis
- Image generation
- TTS (Persian - edge-tts)
- STT (Google Speech Recognition - free)
- Rate limiting (3 sec)
- Group mode (mention/reply to @ShadowFariborz_bot only)
