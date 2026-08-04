/**
 * 🤖 Fariborz Bot - Cloudflare Worker v2
 * Telegram Bot → Cloudflare Worker → Railway API → AI Model
 * 
 * قابلیت‌ها: چت، ویس، عکس، TTS، STT
 */

const RATE_LIMIT_SECONDS = 5;

export default {
  async fetch(request, env) {
    try {
      if (request.method === 'POST') {
        const update = await request.json();
        if (update.message || update.callback_query) {
          await handleUpdate(update, env);
        }
        return new Response('OK', { status: 200 });
      }
      return new Response('Fariborz Bot v2 is running!', { status: 200 });
    } catch (e) {
      console.error('Error:', e);
      return new Response('Error', { status: 500 });
    }
  }
};

// ── Main Handler ────────────────────────────────────────────────────
async function handleUpdate(update, env) {
  const msg = update.message || update.callback_query?.message;
  if (!msg) return;

  const chatId = msg.chat.id;
  const userId = msg.from?.id;
  const name = msg.from?.first_name || '';
  const text = (msg.text || msg.caption || '').toString();
  const isAdmin = String(userId) === env.ADMIN_ID;

  // Rate limit
  const rlKey = `rl_${userId}`;
  const last = await env.CHAT_HISTORY.get(rlKey);
  if (last && (Date.now() - parseInt(last)) / 1000 < RATE_LIMIT_SECONDS) {
    return;
  }
  await env.CHAT_HISTORY.put(rlKey, String(Date.now()));

  // ── Commands ──────────────────────────────────────────────────
  if (text === '/start') {
    return sendMsg(chatId, `سلام ${name}! 👋\nمن فریبرز هستم.\n\n💬 متن بفرست\n🎤 ویس بفرست\n🎨 بگو "عکس بساز"`, env);
  }
  if (text === '/help') {
    return sendMsg(chatId, `📋 راهنما:\n\n💬 هر متنی → جواب\n🎤 ویس → میفهمم\n🎨 "عکس بساز از ..." → عکس\n🔊 "ویس بفرست ..." → صدا\n🔍 "سرچ کن ..." → جستجو`, env);
  }

  // ── Voice (STT) ───────────────────────────────────────────────
  if (msg.voice) {
    return await handleVoice(msg, chatId, userId, name, env);
  }

  // ── Photo (Image Understanding) ───────────────────────────────
  if (msg.photo) {
    return await handlePhoto(msg, chatId, userId, name, text, env);
  }

  // ── Image Generation ──────────────────────────────────────────
  if (text.match(/^(عکس|تصویر)\s*(بساز|بکن)/i) || text.startsWith('/generate-image')) {
    const prompt = text.replace(/^(عکس|تصویر)\s*(بساز|بکن)\s*/i, '').replace(/^\/generate-image\s*/i, '').trim();
    if (!prompt) return sendMsg(chatId, '🎨 موضوع عکس رو بگو!\nمثال: عکس بساز از گربه', env);
    return await handleImageGen(prompt, chatId, env);
  }

  // ── TTS ───────────────────────────────────────────────────────
  if (text.match(/^(ویس|صدا)\s*(بفرست|بده)/i) || text.startsWith('/voice')) {
    const ttsText = text.replace(/^(ویس|صدا)\s*(بفرست|بده)\s*/i, '').replace(/^\/voice\s*/i, '').trim();
    if (!ttsText) return sendMsg(chatId, '🔊 متن رو بگو!\nمثال: ویس بفرست سلام', env);
    return await handleTTS(ttsText, chatId, env);
  }

  // ── Chat ──────────────────────────────────────────────────────
  if (text) {
    return await handleChat(text, chatId, userId, name, env);
  }
}

// ── Voice → Text → Chat ────────────────────────────────────────────
async function handleVoice(msg, chatId, userId, name, env) {
  try {
    await sendAction(chatId, 'record_voice', env);

    // Download voice
    const file = await tgApi('getFile', { file_id: msg.voice.file_id }, env);
    if (!file?.result?.file_path) return sendMsg(chatId, '❌ خطا در دانلود صدا', env);

    const voiceRes = await fetch(`https://api.telegram.org/file/bot${env.TELEGRAM_BOT_TOKEN}/${file.result.file_path}`);
    const buf = await voiceRes.arrayBuffer();
    const b64 = bufToB64(buf);

    // STT
    const stt = await apiPost('/speech-to-text', { audio_base64: b64 }, env);
    if (!stt?.text) return sendMsg(chatId, '❌ نتونستم صدا رو بفهمم', env);

    await sendMsg(chatId, `🎤 شنیدم: "${stt.text}"`, env);
    await handleChat(stt.text, chatId, userId, name, env);
  } catch (e) {
    console.error('Voice error:', e);
    await sendMsg(chatId, '❌ خطا در پردازش صدا', env);
  }
}

// ── Photo → Image Understanding → Chat ─────────────────────────────
async function handlePhoto(msg, chatId, userId, name, text, env) {
  try {
    await sendAction(chatId, 'typing', env);

    const photo = msg.photo[msg.photo.length - 1];
    const file = await tgApi('getFile', { file_id: photo.file_id }, env);
    if (!file?.result?.file_path) return sendMsg(chatId, '❌ خطا در دانلود عکس', env);

    const photoRes = await fetch(`https://api.telegram.org/file/bot${env.TELEGRAM_BOT_TOKEN}/${file.result.file_path}`);
    const buf = await photoRes.arrayBuffer();
    const b64 = bufToB64(buf);

    const prompt = text || 'این عکس رو توصیف کن';
    await handleChat(prompt, chatId, userId, name, env, b64);
  } catch (e) {
    console.error('Photo error:', e);
    await sendMsg(chatId, '❌ خطا در پردازش عکس', env);
  }
}

// ── Image Generation ───────────────────────────────────────────────
async function handleImageGen(prompt, chatId, env) {
  try {
    await sendAction(chatId, 'upload_photo', env);

    const res = await apiPost('/generate-image', { prompt }, env);
    if (!res?.image_base64) return sendMsg(chatId, '❌ نتونستم عکس بسازم', env);

    const imgBuf = b64ToBuf(res.image_base64);
    const blob = new Blob([imgBuf], { type: 'image/jpeg' });

    const fd = new FormData();
    fd.append('chat_id', String(chatId));
    fd.append('photo', blob, 'image.jpg');
    fd.append('caption', `🎨 ${prompt}`);

    await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendPhoto`, { method: 'POST', body: fd });
  } catch (e) {
    console.error('Image gen error:', e);
    await sendMsg(chatId, '❌ خطا در ساخت عکس', env);
  }
}

// ── Text-to-Speech ─────────────────────────────────────────────────
async function handleTTS(text, chatId, env) {
  try {
    await sendAction(chatId, 'record_voice', env);

    const res = await apiPost('/text-to-speech', { text }, env);
    if (!res?.audio_base64) return sendMsg(chatId, '❌ نتونستم صدا بسازم', env);

    const audBuf = b64ToBuf(res.audio_base64);
    const blob = new Blob([audBuf], { type: 'audio/mpeg' });

    const fd = new FormData();
    fd.append('chat_id', String(chatId));
    fd.append('voice', blob, 'voice.mp3');

    await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendVoice`, { method: 'POST', body: fd });
  } catch (e) {
    console.error('TTS error:', e);
    await sendMsg(chatId, '❌ خطا در تولید صدا', env);
  }
}

// ── Chat ───────────────────────────────────────────────────────────
async function handleChat(text, chatId, userId, name, env, imageB64 = null) {
  try {
    await sendAction(chatId, 'typing', env);

    // History
    const hKey = `hist_${chatId}`;
    const hJson = await env.CHAT_HISTORY.get(hKey);
    let history = hJson ? JSON.parse(hJson) : [];

    const body = {
      message: text,
      user_id: String(userId),
      user_name: name,
      history: history
    };
    if (imageB64) body.image_base64 = imageB64;

    const res = await apiPost('/chat', body, env);
    
    // Check for errors
    if (res?.error) {
      console.error('API returned error:', res.error);
      await sendMsg(chatId, `⚠️ ${res.error}`, env);
      return;
    }
    
    const reply = res?.response || res?.message || 'پاسخی دریافت نشد';
    await sendMsg(chatId, reply, env);

    // Update history
    history.push({ role: 'user', text, timestamp: Date.now() });
    history.push({ role: 'assistant', text: reply, timestamp: Date.now() });
    if (history.length > 20) history = history.slice(-20);
    await env.CHAT_HISTORY.put(hKey, JSON.stringify(history));
  } catch (e) {
    console.error('Chat error:', e);
    await sendMsg(chatId, `❌ خطا: ${e.message}`, env);
  }
}

// ── Helpers ────────────────────────────────────────────────────────
async function sendMsg(chatId, text, env) {
  await tgApi('sendMessage', { chat_id: chatId, text }, env);
}

async function sendAction(chatId, action, env) {
  await tgApi('sendChatAction', { chat_id: chatId, action }, env);
}

async function tgApi(method, body, env) {
  const res = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return res.json();
}

async function apiPost(path, body, env) {
  try {
    const res = await fetch(`${env.API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: env.API_SECRET, ...body })
    });
    
    const data = await res.json();
    
    // Check if API returned an error
    if (data.error || data.response?.includes('Error')) {
      console.error(`API ${path} error:`, data);
      return { error: data.error || data.response || 'API Error' };
    }
    
    return data;
  } catch (e) {
    console.error(`API ${path} fetch error:`, e);
    return { error: 'Connection error' };
  }
}

function bufToB64(buf) {
  const bytes = new Uint8Array(buf);
  let bin = '';
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

function b64ToBuf(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}
