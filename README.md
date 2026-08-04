# 🤖 Hermes Bot - Telegram AI Bot

یک بات تلگرام هوش مصنوعی کامل. فقط توکن‌ها رو پر کن و دیپلوی کن!

## 🚀 نصب (یه کلیک!)

### مرحله ۱: Fork کن
[![Fork on GitHub](https://img.shields.io/badge/Fork-GitHub-24292e?style=for-the-badge&logo=github)](https://github.com/shadowfariborz/hermes-bot/fork)

### مرحله ۲: Railway دیپلوی کن
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new?template=https%3A%2F%2Fgithub.com%2Fshadowfariborz%2Fhermes-bot)

### مرحله ۳: متغیرها رو پر کن
فقط این ۴ تا رو عوض کن:

| متغیر | چی بذاری |
|--------|----------|
| `TELEGRAM_BOT_TOKEN` | توکن رباتت از @BotFather |
| `ADMIN_ID` | آیدی عددی خودت از @userinfobot |
| `AI_API_KEY` | کلید API از OpenRouter یا OpenAI |
| `API_SECRET` | یه رمز تصادفی (مثلاً `my-secret-123`) |

بقیه متغیرها **از پیش تنظیم شده** و نیازی به تغییر نداره!

## ✨ امکانات

- 💬 **چت هوش مصنوعی** - جواب به سوالات
- 📸 **تحلیل عکس** - فرستادن عکس و توصیفش
- 🔍 **جستجو در اینترنت** - اطلاعات به‌روز
- 📰 **اخبار لحظه‌ای** - Al Jazeera, CNBC
- 🗄️ **جستجو در دیتابیس** - جستجو در اطلاعات
- ⏰ **زمانبندی** - ارسال خودکار خبر

## 📝 مثال استفاده

به رباتت اینا رو بگو:
- "سلام"
- "مهم‌ترین خبر الان چیه؟"
- "این عکس چیه؟" + عکس بفرست
- "دیتابیس رو سرچ کن: GitHub"

## 🔧 تنظیمات پیشرفته

### تغییر مدل AI
```
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=anthropic/claude-3-opus
```

### اتصال به دیتابیس GitHub
```
GITHUB_TOKEN=ghp_xxx
GITHUB_REPO=shadowfariborz/hermesBackup
```

## 🐛 مشکلات؟

1. **بات جواب نمیده** → توکن‌ها رو چک کن
2. **خطای 401** → `API_SECRET` رو عوض کن
3. **خبر نمیاد** → اینترنت سرور رو چک کن

## 📄 لایسنس

MIT - آزاد برای استفاده
