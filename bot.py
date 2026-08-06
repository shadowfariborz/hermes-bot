"""
🤖 Fariborz Bot - Python/Flask version for Railway
Combined from: hermes_bot_final.js + 0.1.0.js
Features: Chat (Hermes API), Photos, Voice STT, TTS, Image Gen,
          Music ID (ACRCloud), Admin Panel, Dino Game, Broadcast, etc.
"""

import os
import json
import time
import hmac
import hashlib
import sqlite3
import base64
import io
import uuid
import threading
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Flask, request, jsonify, Response
import requests

# ─── Config ────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
HERMES_API_URL = os.environ.get("HERMES_API_URL", "")
API_SECRET = os.environ.get("API_SECRET", "fariborz-hermes-2024")
ADMIN_ID = os.environ.get("ADMIN_ID", "")
ADMIN2_ID = os.environ.get("ADMIN2_ID", "")
ACR_HOST = os.environ.get("ACR_HOST", "")
ACR_ACCESS_KEY = os.environ.get("ACR_ACCESS_KEY", "")
ACR_SECRET_KEY = os.environ.get("ACR_SECRET_KEY", "")
PORT = int(os.environ.get("PORT", 8000))

REQUIRED_CHANNELS = [
    {"username": "@nuxaldev", "url": "https://t.me/nuxaldev", "name": "Nuxaldev"},
    {"username": "@FutureeeProcess", "url": "https://t.me/FutureeeProcess", "name": "Future Process"},
]

RATE_LIMIT_SECONDS = 3
MENTION_PATTERNS = ["فریبرز", "fariborz", "@fariborz_bot", "@nuxal_bot"]

# ─── Database ──────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bot.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

_db_lock = threading.Lock()

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS chat_history (chat_id TEXT, role TEXT, text TEXT, timestamp INTEGER);
        CREATE TABLE IF NOT EXISTS game_scores (user_id TEXT PRIMARY KEY, name TEXT, score INTEGER, created_at INTEGER);
        CREATE TABLE IF NOT EXISTS bans (user_id TEXT PRIMARY KEY, name TEXT, reason TEXT, offense INTEGER, banned_at INTEGER, unban_at INTEGER, is_permanent INTEGER);
        CREATE TABLE IF NOT EXISTS game_sessions (token TEXT PRIMARY KEY, user_id TEXT, name TEXT, start_ts INTEGER);
    """)
    conn.commit()
    conn.close()

init_db()

def kv_get(key):
    with _db_lock:
        conn = get_db()
        row = conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        conn.close()
    return row["value"] if row else None

def kv_set(key, value):
    with _db_lock:
        conn = get_db()
        conn.execute("INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()

def kv_delete(key):
    with _db_lock:
        conn = get_db()
        conn.execute("DELETE FROM kv WHERE key=?", (key,))
        conn.commit()
        conn.close()

def kv_get_json(key):
    v = kv_get(key)
    return json.loads(v) if v else None

def kv_set_json(key, data):
    kv_set(key, json.dumps(data, ensure_ascii=False))

# ─── Telegram API ─────────────────────────────────────────────────────
TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def tg(method, **kwargs):
    try:
        r = requests.post(f"{TG_API}/{method}", json=kwargs, timeout=15)
        return r.json()
    except Exception as e:
        print(f"TG API error {method}: {e}")
        return {"ok": False}

def send_msg(chat_id, text, reply_to=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    return tg("sendMessage", **payload)

def send_action(chat_id, action):
    return tg("sendChatAction", chat_id=chat_id, action=action)

def send_photo(chat_id, photo_bytes, caption=""):
    try:
        url = f"{TG_API}/sendPhoto"
        files = {"photo": ("image.jpg", photo_bytes, "image/jpeg")}
        data = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption
        r = requests.post(url, files=files, data=data, timeout=30)
        return r.json()
    except Exception as e:
        print(f"Send photo error: {e}")
        return {"ok": False}

def send_voice(chat_id, audio_bytes):
    try:
        url = f"{TG_API}/sendVoice"
        files = {"voice": ("voice.mp3", audio_bytes, "audio/mpeg")}
        data = {"chat_id": str(chat_id)}
        r = requests.post(url, files=files, data=data, timeout=30)
        return r.json()
    except Exception as e:
        print(f"Send voice error: {e}")
        return {"ok": False}

def download_tg_file(file_id):
    try:
        info = tg("getFile", file_id=file_id)
        if not info.get("ok"):
            return None
        path = info["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{path}"
        r = requests.get(url, timeout=30)
        return r.content
    except Exception as e:
        print(f"Download file error: {e}")
        return None

# ─── Hermes API ────────────────────────────────────────────────────────
def hermes_post(endpoint, body):
    try:
        r = requests.post(
            f"{HERMES_API_URL}{endpoint}",
            json={"token": API_SECRET, **body},
            timeout=120
        )
        data = r.json()
        if data.get("error"):
            return {"error": data["error"]}
        return data
    except Exception as e:
        print(f"Hermes API error {endpoint}: {e}")
        return {"error": "خطا در اتصال به سرور"}

# ─── Persian Date ──────────────────────────────────────────────────────
def get_persian_date():
    tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tz)
    gy, gm, gd = now.year, now.month, now.day
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    weekdays = ["یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه"]
    months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
    wd = weekdays[now.weekday()]
    return {
        "full": f"{wd}، {jd} {months[jm-1]} {jy}",
        "time": f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}",
        "weekday": wd, "day": jd, "month": months[jm-1], "year": jy
    }

# ─── ACRCloud Music ID ────────────────────────────────────────────────
def hmac_sha1_sign(data, secret):
    return base64.b64encode(
        hmac.new(secret.encode(), data.encode(), hashlib.sha1).digest()
    ).decode()

def acr_identify(audio_bytes):
    if not ACR_HOST or not ACR_ACCESS_KEY or not ACR_SECRET_KEY:
        return None
    ts = str(int(time.time()))
    sig_str = f"POST\n/v1/identify\n{ACR_ACCESS_KEY}\naudio\n1\n{ts}"
    sig = hmac_sha1_sign(sig_str, ACR_SECRET_KEY)
    data = {
        "access_key": ACR_ACCESS_KEY,
        "data_type": "audio",
        "signature_version": "1",
        "signature": sig,
        "timestamp": ts,
        "sample_bytes": str(len(audio_bytes)),
    }
    files = {"sample": ("audio.wav", audio_bytes, "audio/wav")}
    try:
        r = requests.post(f"https://{ACR_HOST}/v1/identify", data=data, files=files, timeout=30)
        return r.json()
    except Exception as e:
        print(f"ACR error: {e}")
        return None

# ─── Admin Helpers ─────────────────────────────────────────────────────
def is_admin(user_id):
    uid = str(user_id)
    if uid == str(ADMIN_ID):
        return True
    if uid == str(ADMIN2_ID):
        return True
    admins = kv_get_json("admin_list") or []
    return any(a.get("userId") == uid for a in admins)

def is_main_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

# ─── Channel Membership ───────────────────────────────────────────────
def check_channels(user_id):
    for ch in REQUIRED_CHANNELS:
        try:
            r = tg("getChatMember", chat_id=ch["username"], user_id=user_id)
            if r.get("ok") and r["result"]["status"] not in ["left", "kicked"]:
                continue
        except:
            pass
        return False
    return True

# ─── Rate Limit ────────────────────────────────────────────────────────
def check_rate_limit(user_id):
    key = f"rl_{user_id}"
    last = kv_get(key)
    if last and (time.time() - float(last)) < RATE_LIMIT_SECONDS:
        return False
    kv_set(key, str(time.time()))
    return True

# ─── Broadcast Groups ─────────────────────────────────────────────────
def save_group(chat_id, title):
    groups = kv_get_json("broadcast_groups") or []
    if not any(g["chat_id"] == chat_id for g in groups):
        groups.append({"chat_id": chat_id, "title": title or f"گروه {chat_id}", "added_at": int(time.time())})
        kv_set_json("broadcast_groups", groups)

def get_broadcast_groups():
    return kv_get_json("broadcast_groups") or []

# ─── Chat History ──────────────────────────────────────────────────────
def get_history(chat_id):
    with _db_lock:
        conn = get_db()
        rows = conn.execute(
            "SELECT role, text FROM chat_history WHERE chat_id=? ORDER BY timestamp DESC LIMIT 20",
            (str(chat_id),)
        ).fetchall()
        conn.close()
    rows.reverse()
    return [{"role": r["role"], "content": r["text"]} for r in rows]

def add_history(chat_id, role, text):
    with _db_lock:
        conn = get_db()
        conn.execute(
            "INSERT INTO chat_history (chat_id, role, text, timestamp) VALUES (?, ?, ?, ?)",
            (str(chat_id), role, text[:500], int(time.time() * 1000))
        )
        # Keep only last 40 messages
        conn.execute(
            "DELETE FROM chat_history WHERE chat_id=? AND timestamp NOT IN "
            "(SELECT timestamp FROM chat_history WHERE chat_id=? ORDER BY timestamp DESC LIMIT 40)",
            (str(chat_id), str(chat_id))
        )
        conn.commit()
        conn.close()

# ─── Game: Anti-Cheat & Ban ───────────────────────────────────────────
def max_plausible_score(elapsed_ms):
    return int((elapsed_ms / 1000) * 15)

def get_active_ban(user_id):
    with _db_lock:
        conn = get_db()
        row = conn.execute("SELECT * FROM bans WHERE user_id=?", (str(user_id),)).fetchone()
        conn.close()
    if not row:
        return None
    if row["unban_at"] and time.time() * 1000 > row["unban_at"]:
        kv_delete(f"ban_{user_id}")
        return None
    return dict(row)

def apply_auto_ban(user_id, name, reason):
    with _db_lock:
        conn = get_db()
        row = conn.execute("SELECT offense FROM bans WHERE user_id=?", (str(user_id),)).fetchone()
        offense = (row["offense"] if row else 0) + 1
        durations = {1: 1, 2: 7, 3: 30, 4: 90, 5: 180, 6: 365}
        is_perm = offense > 6
        days = 36500 if is_perm else durations.get(offense, 365)
        unban_at = None if is_perm else time.time() * 1000 + days * 86400000
        conn.execute(
            "INSERT OR REPLACE INTO bans (user_id, name, reason, offense, banned_at, unban_at, is_permanent) VALUES (?,?,?,?,?,?,?)",
            (str(user_id), name, reason, offense, int(time.time() * 1000), unban_at, 1 if is_perm else 0)
        )
        conn.commit()
        conn.close()
    return {"offense": offense, "days": days, "is_permanent": is_perm}

def submit_game_score(user_id, name, score):
    with _db_lock:
        conn = get_db()
        row = conn.execute("SELECT score FROM game_scores WHERE user_id=?", (str(user_id),)).fetchone()
        if row and score <= row["score"]:
            conn.close()
            rank = conn.execute("SELECT COUNT(*) as c FROM game_scores WHERE score>?", (score,)).fetchone()["c"] + 1 if False else 0
            return {"success": True, "score": score, "rank": 0, "total": 0}
        conn.execute(
            "INSERT OR REPLACE INTO game_scores (user_id, name, score, created_at) VALUES (?, ?, ?, ?)",
            (str(user_id), name, score, int(time.time()))
        )
        rank = conn.execute("SELECT COUNT(*) as c FROM game_scores WHERE score>?", (score,)).fetchone()["c"] + 1
        total = conn.execute("SELECT COUNT(*) as c FROM game_scores").fetchone()["c"]
        conn.commit()
        conn.close()
    return {"success": True, "score": score, "rank": rank, "total": total}

def get_leaderboard():
    with _db_lock:
        conn = get_db()
        rows = conn.execute("SELECT user_id, name, score FROM game_scores ORDER BY score DESC LIMIT 10").fetchall()
        conn.close()
    return [dict(r) for r in rows]

def validate_telegram_init_data(init_data, bot_token):
    try:
        from urllib.parse import parse_qs
        params = parse_qs(init_data)
        hash_val = params.pop("hash", [None])[0]
        if not hash_val:
            return None
        sorted_str = "\n".join(f"{k}={v[0]}" for k, v in sorted(params.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        sig = hmac.new(secret_key, sorted_str.encode(), hashlib.sha256).hexdigest()
        if sig != hash_val:
            return None
        user = json.loads(params.get("user", ["{}"])[0])
        return {"userId": str(user.get("id", "")), "firstName": user.get("first_name", "")}
    except:
        return None

# ─── Help Text ─────────────────────────────────────────────────────────
HELP_TEXT = """🤖 راهنمای کامل ربات فریبرز 🤖

✨ من فریبرز هستم، یک ربات هوشمند فارسی!

━━━━━━━━━━━━━━━━━━━━━━━━
🔄 کامندهای عمومی:

🔹 /start - شروع کار 🚀
🔹 /help - راهنما 📚
🔹 /new - گفتگوی جدید 🔄
🔹 /ping - تست سرعت 🏓
🔹 /dice - تاس 🎲
🔹 /time - ساعت ⏰
🔹 /date - تاریخ 📅
🔹 /dol - پروکسی 🎁
🔹 /pv - پیام خصوصی 💬
🔹 /game - بازی دایناسور 🦖
🔹 /top - رتبه‌بندی 🏆

━━━━━━━━━━━━━━━━━━━━━━━━
💬 چت هوشمند:
• هر متنی → جواب
• عکس → توضیح
• ویس → میفهمم + جواب
• "عکس بساز ..." → عکس
• "ویس بفرست ..." → صدا

━━━━━━━━━━━━━━━━━━━━━━━━
🛠️ کامندهای ادمین (فقط پی‌وی):
🔹 /list - لیست کلمات
🔹 /adddol - اضافه کردن دول
🔹 /broadcast - ارسال همگانی
🔹 /welcome - پیام خوش‌آمد
🔹 /admins - مدیریت ادمین‌ها
🔹 /panel - پنل ادمین

⭐ هر سوالی داری بپرس! 😊"""

# ─── Flask App ─────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "Fariborz Bot v5 (Python) is running! ✅"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/setup", methods=["GET"])
def setup_webhook():
    url = request.url_root.rstrip("/")
    r = tg("setWebhook", url=url)
    return f"Webhook setup: {json.dumps(r)}"

@app.route("/help", methods=["GET"])
def help_page():
    return Response(HELP_TEXT, content_type="text/plain; charset=utf-8")

@app.route("/dino-game", methods=["GET"])
def dino_game():
    """Redirect to game play page with Telegram user data."""
    # This page reads TG WebApp user and redirects
    return """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><script src="https://telegram.org/js/telegram-web-app.js"></script></head><body style="background:#000;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;font-family:system-ui"><div style="text-align:center"><div style="font-size:18px">Loading...</div></div><script>(function(){try{var tg=window.Telegram?.WebApp;if(tg){tg.ready();tg.expand();var u=tg.initDataUnsafe?.user;if(u){window.location.replace("/dino-game/play?user_id="+encodeURIComponent(String(u.id))+"&name="+encodeURIComponent(String(u.first_name||"")));return}}window.location.replace("/dino-game/play")}catch(e){window.location.replace("/dino-game/play")}})();</script></body></html>"""

@app.route("/dino-game/play", methods=["GET"])
def dino_game_play():
    base_url = request.url_root.rstrip("/")
    return Response(DINO_GAME_HTML.replace("{{BASE_URL}}", base_url), content_type="text/html; charset=utf-8")

@app.route("/api/game/leaderboard", methods=["GET"])
def game_leaderboard():
    lb = get_leaderboard()
    return jsonify(lb), 200, {"Access-Control-Allow-Origin": "*"}

@app.route("/api/game/session/start", methods=["POST"])
def game_session_start():
    try:
        body = request.json
        auth = validate_telegram_init_data(body.get("initData", ""), TELEGRAM_BOT_TOKEN)
        if not auth:
            return jsonify({"error": "Invalid auth"}), 401
        ban = get_active_ban(auth["userId"])
        if ban:
            return jsonify({"error": "banned"}), 403
        token = str(uuid.uuid4())
        with _db_lock:
            conn = get_db()
            conn.execute("INSERT OR REPLACE INTO game_sessions (token, user_id, name, start_ts) VALUES (?,?,?,?)",
                         (token, auth["userId"], auth["firstName"], int(time.time() * 1000)))
            conn.commit()
            conn.close()
        return jsonify({"token": token})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/game/ban-status", methods=["POST"])
def game_ban_status():
    try:
        body = request.json
        auth = validate_telegram_init_data(body.get("initData", ""), TELEGRAM_BOT_TOKEN)
        if not auth:
            return jsonify({"banned": False})
        ban = get_active_ban(auth["userId"])
        if not ban:
            return jsonify({"banned": False})
        return jsonify({"banned": True, "reason": ban["reason"], "offense": ban["offense"]})
    except:
        return jsonify({"banned": False})

@app.route("/api/game/submit", methods=["POST"])
def game_submit():
    try:
        body = request.json
        auth = validate_telegram_init_data(body.get("initData", ""), TELEGRAM_BOT_TOKEN)
        if not auth:
            return jsonify({"error": "Invalid auth"}), 401
        ban = get_active_ban(auth["userId"])
        if ban:
            return jsonify({"error": "banned"}), 403
        token = body.get("token")
        if not token:
            return jsonify({"error": "Missing token"}), 400
        with _db_lock:
            conn = get_db()
            session = conn.execute("SELECT * FROM game_sessions WHERE token=?", (token,)).fetchone()
            if not session or session["user_id"] != auth["userId"]:
                conn.close()
                return jsonify({"error": "Invalid session"}), 400
            conn.execute("DELETE FROM game_sessions WHERE token=?", (token,))
            conn.commit()
            conn.close()
        ns = int(body.get("score", 0))
        if ns < 0:
            return jsonify({"error": "Bad score"}), 400
        elapsed = int(time.time() * 1000) - session["start_ts"]
        if ns > max_plausible_score(elapsed):
            return jsonify({"error": "Score inconsistent"}), 400
        if ns > 2000:
            ban_result = apply_auto_ban(auth["userId"], auth["firstName"], "تقلب در بازی")
            try:
                ban_text = f"🚫 شما بن شدید!\n\n📋 دلیل: تقلب در بازی\n🔢 دفعه: {ban_result['offense']}\n⏰ مدت: {'دائمی 🔴' if ban_result['is_permanent'] else str(ban_result['days']) + ' روز'}"
                send_msg(auth["userId"], ban_text)
            except:
                pass
            return jsonify({"error": "banned"}), 403
        result = submit_game_score(auth["userId"], auth["firstName"], ns)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ─── Main Webhook ──────────────────────────────────────────────────────
@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.json
        if not data:
            return "OK"

        # Handle callback_query
        if "callback_query" in data:
            cq = data["callback_query"]
            cd = cq["data"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            cb_id = cq["id"]
            cb_user = str(cq["from"]["id"])

            if cd == "show_config":
                config_text = kv_get("config") or "کانفیگی اضافه نشده."
                if "<pre>" not in config_text:
                    config_text = f"<pre><code>{config_text}</code></pre>"
                tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                   text=f"⚙️ <b>ساب:</b>\n\n{config_text}\n\n📱 <b>برنامه مورد نیاز:</b>",
                   parse_mode="HTML",
                   reply_markup={"inline_keyboard": [
                       [{"text": "Android", "url": "https://play.google.com/store/apps/details?id=app.hiddify.com"},
                        {"text": "iOS", "url": "https://apps.apple.com/us/app/hiddify-proxy-vpn/id6596777532"}],
                       [{"text": "Windows", "url": "https://github.com/hiddify/hiddify-app/releases/download/v4.1.1/Hiddify-Windows-Setup-x64.exe"},
                        {"text": "macOS", "url": "https://github.com/hiddify/hiddify-app/releases/download/v4.1.1/Hiddify-MacOS.dmg"}],
                       [{"text": "Linux", "url": "https://github.com/hiddify/hiddify-app/releases/download/v4.1.1/Hiddify-Linux-x64.AppImage"}],
                       [{"text": "🔙 بازگشت", "callback_data": "back_to_dol"}]
                   ]})
                tg("answerCallbackQuery", callback_query_id=cb_id)
                return "OK"

            if cd == "back_to_dol":
                dol_text = kv_get("dol_inline") or "🎁 لیست دول‌ها خالی است!"
                tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                   text=dol_text,
                   reply_markup={"inline_keyboard": [[{"text": "⚙️ ساب", "callback_data": "show_config"}]]})
                tg("answerCallbackQuery", callback_query_id=cb_id)
                return "OK"

            tg("answerCallbackQuery", callback_query_id=cb_id)
            return "OK"

        # Handle message
        msg = data.get("message")
        if not msg:
            return "OK"

        chat_id = msg["chat"]["id"]
        user_id = str(msg["from"]["id"])
        name = msg["from"].get("first_name", "")
        text = (msg.get("text") or msg.get("caption") or "").strip()
        chat_type = msg["chat"]["type"]
        is_private = chat_type == "private"
        is_group = not is_private
        msg_id = msg["message_id"]
        has_photo = "photo" in msg
        has_voice = "voice" in msg

        # Rate limit
        if not check_rate_limit(user_id):
            return "OK"

        # Save group
        if is_group:
            save_group(chat_id, msg["chat"].get("title", ""))

        # Welcome new members
        if msg.get("new_chat_members"):
            for m in msg["new_chat_members"]:
                if str(m["id"]) != TELEGRAM_BOT_TOKEN.split(":")[0]:
                    dates = get_persian_date()
                    welcome = kv_get_json("welcome_message")
                    if welcome and welcome.get("enabled"):
                        wt = welcome["text"]
                        wt = wt.replace("!mention", f'[{m.get("first_name", "کاربر")}](tg://user?id={m["id"]})')
                        wt = wt.replace("!firstname", m.get("first_name", ""))
                        wt = wt.replace("!groupname", msg["chat"].get("title", "گروه"))
                    else:
                        un = m.get("first_name", "کاربر")
                        gn = msg["chat"].get("title", "ما")
                        wt = f'👋 **خوش آمدی** [{un}](tg://user?id={m["id"]}) عزیز!\n\nبه گروه **{gn}** خوش اومدی 🎉\n\n⏰ {dates["time"]}\n📅 {dates["full"]}\n\nمن فریبرزم، هر سوالی داشتی بگو 😊'
                    tg("sendMessage", chat_id=chat_id, text=wt, parse_mode="Markdown")
            return "OK"

        # Goodbye
        if msg.get("left_chat_member"):
            m = msg["left_chat_member"]
            dates = get_persian_date()
            un = m.get("first_name", "کاربر")
            gn = msg["chat"].get("title", "ما")
            lt = f'👋 **خداحافظ** [{un}](tg://user?id={m["id"]}) عزیز!\n\nاز گروه **{gn}** رفتی 😔\n\n⏰ {dates["time"]}\n📅 {dates["full"]}\n\nامیدوارم دوباره برگردی! 💙'
            tg("sendMessage", chat_id=chat_id, text=lt, parse_mode="Markdown")
            return "OK"

        # Group: only respond when mentioned/replied
        if is_group:
            reply_from = (msg.get("reply_to_message") or {}).get("from", {})
            is_reply_bot = reply_from.get("username") in ["ShadowFariborz_bot", "nuxal_bot"]
            is_mentioned = any(p.lower() in text.lower() for p in MENTION_PATTERNS)
            if not is_reply_bot and not is_mentioned:
                return "OK"
            for p in MENTION_PATTERNS:
                text = text.replace(p, "").strip()

        # ── Music Identification (voice/audio/video) ──
        if has_voice or ("audio" in msg) or ("video" in msg and (msg["video"].get("duration", 0) <= 30)):
            try:
                send_action(chat_id, "record_voice")
                file_id = msg.get("voice", msg.get("audio", msg.get("video", {}))).get("file_id")
                audio_data = download_tg_file(file_id)
                if audio_data:
                    result = acr_identify(audio_data)
                    if result and result.get("status", {}).get("code") == 0:
                        music = result.get("metadata", {}).get("music", [{}])[0]
                        song_info = f'🎵 *آهنگ شناسایی شد!*\n\n🎶 نام: *{music.get("title", "ناشناس")}*\n👤 خواننده: *{music.get("artists", [{}])[0].get("name", "ناشناس")}*\n💿 آلبوم: *{music.get("album", {}).get("name", "ناشناس")}*\n📊 دقت: *{music.get("score", 0)}%*'
                        send_msg(chat_id, song_info, msg_id)
                    else:
                        send_msg(chat_id, "❌ آهنگی پیدا نشد", msg_id)
            except Exception as e:
                print(f"Music ID error: {e}")
            return "OK"

        # ── Commands ──
        cmd_parts = text.split(None, 1) if text.startswith("/") else ["", ""]
        command = cmd_parts[0][1:].lower() if cmd_parts[0].startswith("/") else ""
        args = cmd_parts[1] if len(cmd_parts) > 1 else ""

        if command == "start":
            send_msg(chat_id, f"سلام {name}! 👋\nمن فریبرز هستم.\n\n💬 متن بفرست\n🎤 ویس بفرست\n🎨 بگو \"عکس بساز\"\n🔊 بگو \"ویس بفرست\"", msg_id)
            return "OK"
        if command == "help":
            send_msg(chat_id, HELP_TEXT, msg_id)
            return "OK"
        if command == "new":
            kv_delete(f"hist_{chat_id}")
            with _db_lock:
                conn = get_db()
                conn.execute("DELETE FROM chat_history WHERE chat_id=?", (str(chat_id),))
                conn.commit()
                conn.close()
            send_msg(chat_id, "🔄 تاریخچه چت پاک شد!", msg_id)
            return "OK"
        if command == "ping":
            st = time.time()
            pm = tg("sendMessage", chat_id=chat_id, text="🏓 پینگ...", reply_to_message_id=msg_id)
            if pm.get("ok"):
                pt = int((time.time() - st) * 1000)
                tg("deleteMessage", chat_id=chat_id, message_id=pm["result"]["message_id"])
                status = "⚡عالی" if pt < 100 else "✅خوب" if pt < 300 else "🤔متوسط" if pt < 600 else "⚠️ضعیف"
                send_msg(chat_id, f"🏓 *پینگ:* {pt}ms {status}", msg_id)
            return "OK"
        if command == "dice":
            tg("sendDice", chat_id=chat_id, emoji="🎲")
            return "OK"
        if command == "time":
            d = get_persian_date()
            send_msg(chat_id, f"⏰ *ساعت:* {d['time']}\n📅 *تاریخ:* {d['full']}", msg_id)
            return "OK"
        if command == "date":
            d = get_persian_date()
            send_msg(chat_id, f"📅 *شمسی:* {d['full']}\n⏰ *ساعت:* {d['time']}", msg_id)
            return "OK"
        if command == "pv":
            try:
                tg("sendMessage", chat_id=user_id, text="سلام! چطور می‌تونم کمکت کنم? 😊")
                if not is_private:
                    send_msg(chat_id, "✅ پیام به پی‌وی ارسال شد!", msg_id)
            except:
                send_msg(chat_id, "❌ بات رو استارت کنید!", msg_id)
            return "OK"
        if command == "game":
            base_url = request.url_root.rstrip("/")
            tg("sendMessage", chat_id=chat_id, text="🦕 *بازی دایناسور!*",
               parse_mode="Markdown",
               reply_markup={"inline_keyboard": [[{"text": "🎮 شروع بازی", "url": f"{base_url}/dino-game"}]]},
               reply_to_message_id=msg_id)
            return "OK"
        if command == "top":
            lb = get_leaderboard()
            t = "🏆 *رتبه‌بندی دایناسور*\n\n"
            if not lb:
                t += "❌ هنوز کسی بازی نکرده!"
            else:
                medals = ["🥇", "🥈", "🥉"]
                for i, s in enumerate(lb):
                    prefix = medals[i] if i < 3 else f"#{i+1}"
                    me = " 👈" if str(s["user_id"]) == user_id else ""
                    t += f"{prefix} {s['name'] or 'بازیکن'}{me} — {s['score']:,}\n"
            send_msg(chat_id, t, msg_id)
            return "OK"
        if command == "dol":
            if is_private or check_channels(user_id):
                dol_text = kv_get("dol_inline")
                if dol_text:
                    kv_set(f"dol_requester_{msg_id}", user_id)
                    tg("sendMessage", chat_id=chat_id, text=dol_text,
                       reply_markup={"inline_keyboard": [[{"text": "⚙️ ساب", "callback_data": "show_config"}]]},
                       reply_to_message_id=msg_id)
                else:
                    send_msg(chat_id, "🎁 *لیست دول‌ها خالی است!*", msg_id)
            else:
                send_msg(chat_id, "⚠️ *برای دریافت دول در کانال‌ها عضو شید:*\n\n📢 @nuxaldev\n🚀 @FutureeeProcess", msg_id)
            return "OK"

        # ── Admin Commands (private only) ──
        if is_private and is_admin(user_id):
            if command == "list":
                dt = kv_get("dol_inline")
                send_msg(chat_id, dt or "📋 لیست خالی.")
                return "OK"
            if command == "adddol":
                if not args:
                    send_msg(chat_id, "📝 `/adddol متن دول`")
                else:
                    kv_set("dol_inline", args)
                    send_msg(chat_id, "✅ *دول اضافه شد!*")
                return "OK"
            if command == "broadcast":
                if not args:
                    send_msg(chat_id, "📝 `/broadcast متن پیام`")
                else:
                    groups = get_broadcast_groups()
                    sent = 0
                    for g in groups:
                        try:
                            tg("sendMessage", chat_id=g["chat_id"], text=args, parse_mode="Markdown")
                            sent += 1
                        except:
                            pass
                    send_msg(chat_id, f"📢 ارسال شد: {sent}/{len(groups)}")
                return "OK"
            if command == "welcome":
                if not args:
                    send_msg(chat_id, "📝 `/welcome متن`\n\nمتغیرها: `!mention` `!firstname` `!groupname`")
                else:
                    kv_set_json("welcome_message", {"enabled": True, "text": args})
                    send_msg(chat_id, "✅ *پیام خوش‌آمدگویی تنظیم شد!*")
                return "OK"
            if command == "admins" and is_main_admin(user_id):
                al = "👨‍💼 *لیست ادمین‌ها:*\n\n"
                if ADMIN_ID:
                    al += f"👑 ادمین اصلی: `{ADMIN_ID}`\n"
                if ADMIN2_ID:
                    al += f"🌟 ادمین دوم: `{ADMIN2_ID}`\n"
                send_msg(chat_id, al)
                return "OK"
            if command == "panel":
                groups = get_broadcast_groups()
                tg("sendMessage", chat_id=chat_id,
                   text=f"👨‍💻 *پنل مدیریت*\n\n📊 گروه‌ها: {len(groups)}\n🔧 /list /adddol /broadcast /welcome /admins",
                   parse_mode="Markdown")
                return "OK"

        # ── Voice → STT → Chat ──
        if has_voice:
            try:
                send_action(chat_id, "record_voice")
                audio_data = download_tg_file(msg["voice"]["file_id"])
                if not audio_data:
                    send_msg(chat_id, "❌ خطا در دانلود صدا", msg_id)
                    return "OK"
                b64 = base64.b64encode(audio_data).decode()
                stt = hermes_post("/speech-to-text", {"audio_base64": b64})
                if not stt.get("text"):
                    send_msg(chat_id, "❌ نتونستم صدا رو بفهمم", msg_id)
                    return "OK"
                send_msg(chat_id, f'🎤 شنیدم: "{stt["text"]}"', msg_id)
                # Continue to chat with STT text
                text = stt["text"]
                has_voice = False
            except Exception as e:
                print(f"Voice error: {e}")
                send_msg(chat_id, "❌ خطا در پردازش صدا", msg_id)
                return "OK"

        # ── Image Generation ──
        if text and (text.startswith("عکس") or text.startswith("تصویر") or text.startswith("/generate-image")):
            prompt = text
            for prefix in ["عکس بساز", "عکس بکن", "تصویر بساز", "تصویر بکن", "/generate-image"]:
                prompt = prompt.replace(prefix, "").strip()
            if not prompt:
                send_msg(chat_id, "🎨 موضوع عکس رو بگو!", msg_id)
                return "OK"
            try:
                send_action(chat_id, "upload_photo")
                res = hermes_post("/generate-image", {"prompt": prompt})
                if not res.get("image_base64"):
                    send_msg(chat_id, "❌ نتونستم عکس بسازم", msg_id)
                    return "OK"
                img_bytes = base64.b64decode(res["image_base64"])
                send_photo(chat_id, img_bytes, f"🎨 {prompt}")
            except Exception as e:
                print(f"Image gen error: {e}")
                send_msg(chat_id, "❌ خطا در ساخت عکس", msg_id)
            return "OK"

        # ── TTS ──
        if text and (text.startswith("ویس") or text.startswith("صدا") or text.startswith("/voice")):
            tts_text = text
            for prefix in ["ویس بفرست", "ویس بده", "صدا بفرست", "صدا بده", "/voice"]:
                tts_text = tts_text.replace(prefix, "").strip()
            if not tts_text:
                send_msg(chat_id, "🔊 متن رو بگو!\nمثال: /voice سلام دنیا", msg_id)
                return "OK"
            try:
                send_action(chat_id, "record_voice")
                res = hermes_post("/text-to-speech", {"text": tts_text})
                if not res.get("audio_base64"):
                    send_msg(chat_id, "❌ نتونستم صدا بسازم", msg_id)
                    return "OK"
                audio_bytes = base64.b64decode(res["audio_base64"])
                send_voice(chat_id, audio_bytes)
            except Exception as e:
                print(f"TTS error: {e}")
                send_msg(chat_id, "❌ خطا در تولید صدا", msg_id)
            return "OK"

        # ── Chat with Hermes ──
        # Build context from reply chain
        context_parts = []
        image_b64 = None

        if has_photo:
            photo_data = download_tg_file(msg["photo"][-1]["file_id"])
            if photo_data:
                image_b64 = base64.b64encode(photo_data).decode()

        current = msg
        depth = 0
        while current.get("reply_to_message") and depth < 5:
            depth += 1
            rm = current["reply_to_message"]
            r_name = rm.get("from", {}).get("first_name", "?")
            r_text = (rm.get("text") or rm.get("caption") or "")[:300]
            if "photo" in rm and not image_b64:
                pd = download_tg_file(rm["photo"][-1]["file_id"])
                if pd:
                    image_b64 = base64.b64encode(pd).decode()
                context_parts.insert(0, f"[عکس از {r_name}]: {r_text}")
            elif "voice" in rm:
                context_parts.insert(0, f"[ویس از {r_name}]: {r_text or '(پیام صوتی)'}")
            else:
                context_parts.insert(0, f"[پیام {r_name}]: {r_text}")
            current = rm

        full_msg = text or "این عکس رو توضیح بده"
        if context_parts:
            full_msg = "\n".join(context_parts) + f"\n[{name}]: {full_msg}"

        # Call Hermes API
        try:
            send_action(chat_id, "typing")
            history = get_history(chat_id)
            body = {"message": full_msg, "user_id": user_id, "user_name": name, "history": history}
            if image_b64:
                body["image_base64"] = image_b64
            res = hermes_post("/chat", body)
            if res.get("error"):
                send_msg(chat_id, f"⚠️ {res['error']}", msg_id)
            else:
                reply = res.get("response", "پاسخی دریافت نشد")
                send_msg(chat_id, reply, msg_id)
                add_history(chat_id, "user", full_msg[:500])
                add_history(chat_id, "assistant", reply[:500])
        except Exception as e:
            print(f"Chat error: {e}")
            send_msg(chat_id, "❌ خطا در پردازش پیام", msg_id)

        return "OK"

    except Exception as e:
        print(f"Webhook error: {e}")
        return "OK"


# ─── Dino Game HTML ────────────────────────────────────────────────────
DINO_GAME_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>Dino Runner</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0f0f23;color:#fff;font-family:system-ui;overflow:hidden;height:100vh;display:flex;align-items:center;justify-content:center}
#game-container{position:relative;width:100%;max-width:400px;height:100vh;max-height:700px}
canvas{width:100%;height:100%;display:block;border-radius:12px}
#ui-overlay{position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none}
#score-display{position:absolute;top:20px;right:20px;font-size:24px;font-weight:bold;text-shadow:2px 2px 4px rgba(0,0,0,.8)}
#start-screen,#game-over-screen{position:absolute;top:0;left:0;right:0;bottom:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(15,15,35,.9);pointer-events:auto;border-radius:12px}
#game-over-screen{display:none}
.title{font-size:32px;margin-bottom:20px}
.subtitle{font-size:16px;color:#aaa;margin-bottom:30px}
.btn{background:linear-gradient(135deg,#667eea,#764ba2);border:none;color:#fff;padding:15px 40px;font-size:18px;border-radius:25px;cursor:pointer}
.score-text{font-size:48px;margin:20px 0}
.rank-text{font-size:18px;color:#ffd700;margin:10px 0}
</style></head>
<body>
<div id="game-container">
<canvas id="gameCanvas"></canvas>
<div id="ui-overlay">
<div id="score-display">0</div>
<div id="start-screen">
<div class="title">🦕 Dino Runner</div>
<div class="subtitle">بپر و رد شو!</div>
<button class="btn" id="startBtn">شروع بازی</button>
</div>
<div id="game-over-screen">
<div class="title">💀 Game Over</div>
<div class="score-text" id="finalScore">0</div>
<div class="rank-text" id="rankText"></div>
<button class="btn" id="restartBtn">دوباره بازی کن</button>
</div>
</div></div>
<script>
const c=document.getElementById('gameCanvas'),x=c.getContext('2d');
let gs='waiting',sc=0,d={x:50,y:0,vy:0,j:false},obs=[],spd=5,fc=0;
let sessionToken=null,userName='';
const BASE='{{BASE_URL}}';

function rz(){const ct=document.getElementById('game-container');c.width=ct.clientWidth*2;c.height=ct.clientHeight*2;x.scale(2,2)}
rz();window.addEventListener('resize',rz);

function jump(){if(!d.j){d.vy=-12;d.j=true}}

document.addEventListener('keydown',e=>{if(e.code==='Space'||e.code==='ArrowUp'){e.preventDefault();if(gs==='playing')jump()}});
c.addEventListener('touchstart',e=>{e.preventDefault();if(gs==='playing')jump()});
c.addEventListener('click',()=>{if(gs==='playing')jump()});

function startGame(){
  const params=new URLSearchParams(window.location.search);
  userName=params.get('name')||'بازیکن';
  fetch(BASE+'/api/game/session/start',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({initData:window.Telegram?.WebApp?.initData||''})})
  .then(r=>r.json()).then(d=>{sessionToken=d.token;gs='playing';sc=0;obs=[];spd=5;fc=0;d.y=0;d.vy=0;d.j=false;
    document.getElementById('start-screen').style.display='none';document.getElementById('game-over-screen').style.display='none'})
  .catch(()=>{gs='playing';sc=0;obs=[];spd=5;fc=0;d.y=0;d.vy=0;d.j=false;
    document.getElementById('start-screen').style.display='none';document.getElementById('game-over-screen').style.display='none'});
}

function gameOver(){
  gs='over';document.getElementById('game-over-screen').style.display='flex';
  document.getElementById('finalScore').textContent=sc.toLocaleString();
  if(sessionToken){
    fetch(BASE+'/api/game/submit',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token:sessionToken,score:sc,initData:window.Telegram?.WebApp?.initData||''})})
    .then(r=>r.json()).then(d=>{
      if(d.rank)document.getElementById('rankText').textContent='رتبه شما: #'+d.rank+' از '+d.total;
      else if(d.error)document.getElementById('rankText').textContent='⚠️ '+d.error;
    }).catch(()=>{});
  }
}

document.getElementById('startBtn').onclick=startGame;
document.getElementById('restartBtn').onclick=startGame;

function loop(){
  requestAnimationFrame(loop);if(gs!=='playing')return;
  fc++;x.fillStyle='#0f0f23';x.fillRect(0,0,c.width/2,c.height/2);
  const W=c.width/2,H=c.height/2,G=H-60;
  // Ground
  x.fillStyle='#333';x.fillRect(0,G,W,3);
  // Dino
  x.fillStyle='#4ade80';x.fillRect(d.x,G-30+d.y,25,30);x.fillStyle='#fff';x.fillRect(d.x+17,G-25+d.y,4,4);
  // Gravity
  d.vy+=0.6;d.y+=d.vy;if(d.y>=0){d.y=0;d.vy=0;d.j=false}
  // Obstacles
  if(fc%Math.max(40,90-Math.floor(sc/50))===0)obs.push({x:W,h:25+Math.random()*20});
  x.fillStyle='#ef4444';
  for(let i=obs.length-1;i>=0;i--){const o=obs[i];o.x-=spd;x.fillRect(o.x,G-o.h,15,o.h);
    if(o.x<d.x+25&&o.x+15>d.x&&G-o.h<G-30+d.y+30){gameOver();return}
    if(o.x<-20)obs.splice(i,1)}
  // Score
  sc++;document.getElementById('score-display').textContent=sc.toLocaleString();
  if(fc%100===0)spd=Math.min(15,spd+0.5);
}
loop();
</script></body></html>"""

# ─── Main ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🤖 Fariborz Bot starting on port {PORT}...")
    print(f"   Hermes API: {HERMES_API_URL}")
    print(f"   Admin ID: {ADMIN_ID}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
