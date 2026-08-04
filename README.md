# 🤖 Hermes Bot - Telegram AI Bot Template

یک بات تلگرام هوش مصنوعی کامل و آماده استقرار. فقط کافیه تنظیمات رو پر کنی و دیپلوی کنی!

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

## ✨ امکانات

- 💬 **چت هوش مصنوعی** - پاسخ به سوالات با مدل‌های مختلف
- 📸 **پشتیبانی از عکس** - تحلیل و توصیف تصاویر
- 🔍 **جستجو در اینترنت** - دریافت اطلاعات به‌روز
- 📰 **اخبار زنده** - از منابع معتبر (Al Jazeera, CNBC)
- 🗄️ **جستجو در دیتابیس** - جستجو در اطلاعات ذخیره شده
- ⏰ **زمانبندی** - ارسال خودکار خبر به تاپیک‌ها
- 📊 **تاریخچه مکالمات** - حافظه برای مکالمات قبلی

## 🚀 نصب سریع (One-Click Deploy)

### روش ۱: Railway Template
1. روی دکمه بالا کلیک کن
2. متغیرهای محیطی رو پر کن
3. دیپلوی کن!

### روش ۲: دستی
```bash
# کلون کردن
git clone https://github.com/yourusername/hermes-bot.git
cd hermes-bot

# نصب (اختیاری - فقط Python استاندارد نیاز داره)
pip install -r requirements.txt

# کپی تنظیمات
cp .env.example .env

# ویرایش .env با اطلاعات خودت
nano .env

# اجرا
python app.py
```

## ⚙️ تنظیمات

### تنظیمات ضروری

| متغیر | توضیح | از کجا بگیریم |
|--------|--------|----------------|
| `TELEGRAM_BOT_TOKEN` | توکن ربات تلگرام | [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | آیدی عددی ادمین | [@userinfobot](https://t.me/userinfobot) |
| `AI_API_KEY` | کلید API هوش مصنوعی | [OpenRouter](https://openrouter.ai/) یا [OpenAI](https://platform.openai.com/) |
| `AI_BASE_URL` | آدرس API مدل | بسته به ارائه‌دهنده |
| `AI_MODEL` | نام مدل | مثلاً `gpt-4` یا `mimoHermes` |
| `API_SECRET` | رمز عبور API | خودت یه رمز تصادفی بذار |

### تنظیمات اختیاری

| متغیر | توضیح |
|--------|--------|
| `GITHUB_TOKEN` | توکن GitHub برای دسترسی به دیتابیس |
| `GITHUB_REPO` | ریپوی دیتابیس (فرمت: `user/repo`) |

## 📁 ساختار پروژه

```
hermes-bot/
├── app.py              # سرور اصلی API (تمام منطق)
├── requirements.txt    # وابستگی‌ها
├── railway.json        # تنظیمات Railway
├── Procfile            # فایل اجرایی
├── .env.example        # نمونه متغیرها
└── README.md           # این راهنما
```

## 🔌 API Endpoints

### `POST /chat`
ارسال پیام به هوش مصنوعی

```json
{
  "message": "سلام",
  "user_id": "123456",
  "user_name": "کاربر",
  "token": "your-api-secret",
  "image_base64": "optional-base64-image",
  "history": []
}
```

### `POST /schedule`
زمانبندی ارسال خودکار خبر

```json
{
  "token": "your-api-secret",
  "chat_id": "-1001234567890",
  "message_thread_id": 123,
  "interval": 300,
  "count": 3
}
```

### `POST /search-db`
جستجو در دیتابیس

```json
{
  "token": "your-api-secret",
  "query": " GitHub"
}
```

### `GET /health`
بررسی وضعیت سرور

## 🛠️ توسعه

### اضافه کردن منابع خبری جدید
```python
def fetch_news():
    sources = [
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362"),
        # منبع جدید اضافه کنید:
        ("منبع جدید", "https://example.com/rss"),
    ]
```

### اضافه کردن مدل جدید
```python
# در .env:
AI_MODEL=anthropic/claude-3-opus
AI_BASE_URL=https://openrouter.ai/api/v1
```

## 🐛 عیب‌یابی

### خطا در اتصال
- بررسی کن توکن‌ها درست هستن
- بررسی کن API سرور در دسترسه

### خطا در دیتابیس
- بررسی کن `GITHUB_TOKEN` و `GITHUB_REPO` درست هستن
- بررسی کن ریپو public هست یا توکن دسترسی داره

## 📝 لایسنس

MIT License - آزاد برای استفاده و تغییر

## 🤝 مشارکت

مشتاقانه منتظر مشارکت شما هستیم! Issues و PRs خوش‌اومده.

## 💬 پشتیبانی

اگه سوالی داشتی، Issue بزن یا مستقیم پیام بده.
