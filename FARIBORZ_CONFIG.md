# 🤖 Fariborz Bot - Working Config (aug 5 2026)

## Cloudflare Worker
- **File:** `worker.js`
- **URL:** https://fariborz.shadowfariborz.workers.dev/

### Variables (Cloudflare)
```
TELEGRAM_BOT_TOKEN = (secret)
ADMIN_ID = 6236206739
CHAT_HISTORY = KV (a2a777fdf4e14a86b735726becf5b9ce)
```

### Hardcoded in worker.js
```
API_URL = "https://vigilant-perfection-production-b218.up.railway.app"
API_SECRET = "fariborz-hermes-2024"
```

---

## Railway API
- **File:** `app.py`
- **URL:** https://vigilant-perfection-production-b218.up.railway.app

### Variables
```
TELEGRAM_BOT_TOKEN = (same)
ADMIN_ID = 6236206739
AI_API_KEY = (OpenRouter key)
AI_BASE_URL = https://openrouter.ai/api/v1
AI_MODEL = google/gemini-2.5-flash
API_SECRET = fariborz-hermes-2024
```

### Endpoints
- POST /chat
- POST /generate-image
- POST /text-to-speech
- POST /speech-to-text

---

## Features (v4)
✅ Chat + History
✅ Reply chain (5 levels)
✅ Photo analysis
✅ Image generation
✅ TTS (Persian)
✅ STT (voice messages)
✅ Rate limiting
✅ Group mode (mention/reply only)

---

## Restore Instructions
1. Deploy `worker.js` to Cloudflare Worker "fariborz"
2. Add KV binding: CHAT_HISTORY
3. Deploy `app.py` to Railway
4. Set variables above
5. pip install edge-tts

## Account IDs
- Cloudflare: 7a840400ce789d28398c9655aa0a522e
- KV Namespace: a2a777fdf4e14a86b735726becf5b9ce
