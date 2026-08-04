#!/usr/bin/env python3
"""
🤖 Hermes Bot - Telegram AI Bot API Server
Version: 1.0
Features: Chat, Image, History, Web Search, News, Database Search, Scheduler
"""

import os
import json
import re
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from html import unescape

# ── Configuration ─────────────────────────────────────────────────────
PORT = int(os.environ.get('PORT', '8080'))
AI_API_KEY = os.environ.get('AI_API_KEY', '')
AI_BASE_URL = os.environ.get('AI_BASE_URL', 'https://openrouter.ai/api/v1')
AI_MODEL = os.environ.get('AI_MODEL', 'google/gemini-2.0-flash-001')
API_SECRET = os.environ.get('API_SECRET', 'change-me-in-production')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
ADMIN_ID = os.environ.get('ADMIN_ID', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO = os.environ.get('GITHUB_REPO', '')

# ── System Prompt ─────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a smart Persian Telegram bot assistant.

You can:
- Search the internet for information
- Read news from reliable sources (Al Jazeera, CNBC)
- Analyze images and photos
- Provide up-to-date answers
- Search through a database

Rules:
- Always respond in Persian
- Be friendly and kind to users
- Use emojis but don't overdo it
- Decide on your own when to greet users
- If someone sends an image, describe it
- If someone asks you to do something, do it (unless against rules)
- If a message is a reply to another message, consider that context
- When asked for news, fetch from RSS feeds and summarize in Persian
- When asked to search the database, use the /search-db endpoint"""

# ── Logging ───────────────────────────────────────────────────────────
def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}", flush=True)

# ── Scheduler ─────────────────────────────────────────────────────────
scheduled_tasks = []

def send_telegram_message(chat_id, text, thread_id=None):
    """Send message via Telegram Bot API"""
    if not BOT_TOKEN:
        log("No BOT_TOKEN set!")
        return False
    
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if thread_id:
        params["message_thread_id"] = thread_id
    
    try:
        data = json.dumps(params).encode('utf-8')
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result.get('ok', False)
    except Exception as e:
        log(f"Telegram send error: {e}")
        return False

def execute_scheduled_task(task):
    """Execute a scheduled news posting task"""
    try:
        log(f"Executing scheduled task: {task.get('description', '?')}")
        
        # Fetch news
        news = fetch_news()
        
        if news:
            # Pick a different news than last time
            last_title = task.get('last_title', '')
            chosen = None
            for n in news:
                if n['title'] != last_title:
                    chosen = n
                    break
            if not chosen:
                chosen = news[0]
            
            task['last_title'] = chosen['title']
            
            # Format message
            msg = f"📰 **خبر فوری**\n\n"
            msg += f"**{chosen['title']}**\n"
            if chosen.get('description'):
                msg += f"\n{chosen['description'][:200]}\n"
            msg += f"\n🔗 منبع: {chosen.get('source', 'نامشخص')}"
            
            # Send to topic
            chat_id = task.get('chat_id')
            thread_id = task.get('thread_id')
            
            if chat_id:
                success = send_telegram_message(chat_id, msg, thread_id)
                log(f"News sent to {chat_id}:{thread_id} - Success: {success}")
        else:
            log("No news found")
        
        # Schedule next execution if needed
        remaining = task.get('remaining', 0)
        if remaining > 0:
            task['remaining'] = remaining - 1
            interval = task.get('interval', 300)
            timer = threading.Timer(interval, execute_scheduled_task, [task])
            timer.daemon = True
            timer.start()
            log(f"Next task in {interval} seconds ({task['remaining']} remaining)")
        
    except Exception as e:
        log(f"Scheduled task error: {e}")

def schedule_task(chat_id, thread_id, interval_seconds, count, description=""):
    """Schedule repeated task"""
    task = {
        'chat_id': chat_id,
        'thread_id': thread_id,
        'interval': interval_seconds,
        'remaining': count - 1,
        'description': description,
        'last_title': ''
    }
    scheduled_tasks.append(task)
    
    # Start first execution
    timer = threading.Timer(5, execute_scheduled_task, [task])
    timer.daemon = True
    timer.start()
    
    return True

# ── Web Search / News Functions ───────────────────────────────────────
def fetch_rss(url, max_items=8):
    """Fetch and parse RSS feed"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; HermesBot/1.0)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
        
        items = []
        for match in re.finditer(r'<item>(.*?)</item>', raw, re.DOTALL):
            item_xml = match.group(1)
            title_m = re.search(r'<title>(.*?)</title>', item_xml)
            desc_m = re.search(r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>', item_xml, re.DOTALL)
            link_m = re.search(r'<link>(.*?)</link>', item_xml)
            
            title = unescape(title_m.group(1).strip()) if title_m else ''
            desc = unescape(desc_m.group(1).strip()) if desc_m else ''
            desc = re.sub(r'<[^>]+>', '', desc).strip()
            link = link_m.group(1).strip() if link_m else ''
            
            if title:
                items.append({'title': title, 'description': desc[:300], 'link': link})
            
            if len(items) >= max_items:
                break
        
        return items
    except Exception as e:
        log(f"RSS error: {e}")
        return []

def fetch_news():
    """Fetch latest news from multiple sources"""
    sources = [
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362"),
    ]
    
    all_news = []
    for name, url in sources:
        items = fetch_rss(url, 5)
        for item in items:
            item['source'] = name
        all_news.extend(items)
    
    return all_news[:15]

def fetch_url_content(url, max_chars=3000):
    """Fetch text content from a URL"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; HermesBot/1.0)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
        
        text = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = unescape(text)
        
        return text[:max_chars]
    except Exception as e:
        return f"Error reading page: {str(e)[:100]}"

def detect_search_intent(message):
    """Detect if user wants web search, news, or database search"""
    msg = message.lower()
    news_keywords = ['خبر', 'اخبار', 'news', 'چه خبر', 'اکنون', 'الان', 'امروز', 'لحظه', 'فوری']
    search_keywords = ['سرچ', 'جستجو', 'search', 'گردش', 'بگرد', 'پیدا کن', 'ببین']
    schedule_keywords = ['زمانبندی', 'زمان‌بندی', 'هر', 'دقیقه', 'بعد', 'فرستاد', 'ارسال کن', 'بفرست']
    db_keywords = ['دیتابیس', 'پایگاه', 'اطلاعات', 'داده', 'database']
    url_pattern = r'https?://[^\s]+'
    
    has_news = any(k in msg for k in news_keywords)
    has_search = any(k in msg for k in search_keywords)
    has_schedule = any(k in msg for k in schedule_keywords)
    has_db = any(k in msg for k in db_keywords)
    has_url = bool(re.search(url_pattern, message))
    
    return has_news, has_search, has_schedule, has_db, has_url

# ── Database Search ───────────────────────────────────────────────────
def search_database(query):
    """Search the database from GitHub"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return []
    
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/hermes_index.json"
        headers = {'User-Agent': 'Mozilla/5.0'}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        
        results = []
        query_lower = query.lower()
        
        for mem in data.get('memories', []):
            if query_lower in mem.get('content', '').lower():
                results.append({
                    'type': 'memory',
                    'file': mem.get('file', ''),
                    'content': mem.get('content', '')[:300]
                })
        
        for skill in data.get('skills', []):
            if query_lower in skill.get('content', '').lower():
                results.append({
                    'type': 'skill',
                    'file': skill.get('file', ''),
                    'content': skill.get('content', '')[:300]
                })
        
        for link in data.get('links', []):
            if query_lower in link.get('url', '').lower():
                results.append({
                    'type': 'link',
                    'url': link.get('url', ''),
                    'source': link.get('source', '')
                })
        
        return results[:10]
    except Exception as e:
        log(f"Database search error: {e}")
        return []

# ── Call AI ───────────────────────────────────────────────────────────
def call_ai(messages, model=None, retries=3):
    """Call AI model with retry logic"""
    log(f"Calling AI: model={model or AI_MODEL}, url={AI_BASE_URL}")
    if not AI_API_KEY:
        log("ERROR: AI_API_KEY not set!")
        return "API key not set!"
    
    url = f"{AI_BASE_URL}/chat/completions"
    payload = {
        "model": model or AI_MODEL,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.7
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}"
    }
    
    import time
    
    for attempt in range(retries):
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = response.read().decode('utf-8')
                
                try:
                    result = json.loads(raw)
                except json.JSONDecodeError:
                    last_brace = raw.rfind('}')
                    if last_brace > 0:
                        result = json.loads(raw[:last_brace+1])
                    else:
                        return "Error parsing response"
                
                if 'choices' in result and len(result['choices']) > 0:
                    message = result['choices'][0].get('message', {})
                    content = message.get('content')
                    reasoning = message.get('reasoning', '')
                    return content or reasoning or "No response"
                return "No response"
                
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                log(f"Rate limited, waiting {wait_time}s (attempt {attempt+1}/{retries})")
                time.sleep(wait_time)
                continue
            log(f"API Error {e.code}")
            return f"API Error: {e.code}"
        except Exception as e:
            log(f"Error: {e}")
            return f"Server Error: {str(e)[:100]}"
    
    return "Rate limit exceeded. Please try again later."

# ── HTTP Handler ─────────────────────────────────────────────────────
class APIHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path == '/health':
            self.send_json({"status": "ok", "model": AI_MODEL, "scheduled": len(scheduled_tasks)})
        elif self.path == '/':
            self.send_json({
                "service": "Hermes Bot API",
                "version": "1.0",
                "model": AI_MODEL,
                "features": ["text", "images", "history", "web_search", "news", "scheduler", "database"],
                "endpoints": {
                    "POST /chat": "Send message + image + history + search",
                    "POST /schedule": "Schedule repeated news posting",
                    "POST /search-db": "Search the database"
                }
            })
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == '/chat':
            self.handle_chat()
        elif self.path == '/schedule':
            self.handle_schedule()
        elif self.path == '/search-db':
            self.handle_search_db()
        else:
            self.send_error(404)
    
    def handle_chat(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            # Auth check
            auth = self.headers.get('Authorization', '')
            token = data.get('token', '')
            if auth != f'Bearer {API_SECRET}' and token != API_SECRET:
                self.send_json({"error": "Unauthorized"}, 401)
                return
            
            message = data.get('message', '')
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            image_base64 = data.get('image_base64', None)
            history = data.get('history', [])
            
            if not message:
                self.send_json({"error": "No message"}, 400)
                return
            
            log(f"Message from {user_name or '?'} ({user_id}): {message[:50]}...")
            
            # Detect intent
            wants_news, wants_search, wants_schedule, wants_db, has_url = detect_search_intent(message)
            
            # Build context with web data if needed
            web_context = ""
            
            if wants_news:
                log("Fetching news...")
                news = fetch_news()
                if news:
                    news_text = "\n".join([
                        f"- [{n.get('source', '?')}] {n['title']}: {n.get('description', '')[:150]}"
                        for n in news
                    ])
                    web_context = f"\n\n[Fresh news from internet:]\n{news_text}\n"
            
            if has_url:
                urls = re.findall(r'https?://[^\s]+', message)
                for url in urls[:2]:
                    log(f"Fetching URL: {url}")
                    content = fetch_url_content(url)
                    web_context += f"\n\n[Content of {url}]:\n{content}\n"
            
            # Build messages
            messages = [{"role": "system", "content": SYSTEM_PROMPT + web_context}]
            
            # Add history
            for h in history[-20:]:
                role = h.get('role', 'user')
                text = h.get('text', '')
                if role == 'model':
                    role = 'assistant'
                if text:
                    messages.append({"role": role, "content": text})
            
            # User message
            user_text = f"[User: {user_name or 'Unknown'}]\n\n{message}"
            
            if image_base64:
                user_content = [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
                messages.append({"role": "user", "content": user_content})
            else:
                messages.append({"role": "user", "content": user_text})
            
            response = call_ai(messages)
            log(f"Response: {response[:50]}...")
            
            self.send_json({
                "response": response,
                "user_id": user_id,
                "model": AI_MODEL,
                "has_image": bool(image_base64),
                "has_history": bool(history),
                "has_web_data": bool(web_context),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            log(f"Error: {e}")
            self.send_json({"error": str(e)}, 500)
    
    def handle_schedule(self):
        """Schedule repeated news posting"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            token = data.get('token', '')
            if token != API_SECRET:
                self.send_json({"error": "Unauthorized"}, 401)
                return
            
            chat_id = data.get('chat_id')
            thread_id = data.get('thread_id')
            interval = data.get('interval', 300)
            count = data.get('count', 3)
            description = data.get('description', 'news posting')
            
            if not chat_id:
                self.send_json({"error": "chat_id required"}, 400)
                return
            
            success = schedule_task(chat_id, thread_id, interval, count, description)
            
            self.send_json({
                "success": success,
                "message": f"Scheduled {count} tasks every {interval} seconds",
                "active_tasks": len(scheduled_tasks)
            })
            
        except Exception as e:
            log(f"Schedule error: {e}")
            self.send_json({"error": str(e)}, 500)
    
    def handle_search_db(self):
        """Search the database"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            token = data.get('token', '')
            if token != API_SECRET:
                self.send_json({"error": "Unauthorized"}, 401)
                return
            
            query = data.get('query', '')
            if not query:
                self.send_json({"error": "query required"}, 400)
                return
            
            log(f"DB Search: {query}")
            results = search_database(query)
            
            self.send_json({
                "query": query,
                "results": results,
                "count": len(results)
            })
            
        except Exception as e:
            log(f"Search error: {e}")
            self.send_json({"error": str(e)}, 500)
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def log_message(self, format, *args):
        pass

def main():
    log(f"🤖 Hermes Bot API v1.0")
    log(f"Port: {PORT}")
    log(f"Model: {AI_MODEL}")
    log(f"Scheduler: Active")
    log(f"Database: {'Connected' if GITHUB_REPO else 'Not configured'}")
    
    server = HTTPServer(('0.0.0.0', PORT), APIHandler)
    log("✅ Running!")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

if __name__ == '__main__':
    main()
