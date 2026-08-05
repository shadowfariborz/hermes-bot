/**
 * 🤖 Fariborz Bot v4 - Cloudflare Worker
 * 
 * ✅ Photos: download + analyze when mentioned
 * ✅ Reply chain: read replied messages + their photos
 * ✅ Chat history/memory
 * ✅ Voice (STT) + Image Gen + TTS
 */

const API_URL = "https://vigilant-perfection-production-b218.up.railway.app";
const API_SECRET = "fariborz-hermes-2024";

export default {
  async fetch(request, env) {
    try {
      if (request.method === 'POST') {
        const update = await request.json();
        if (update.message) {
          await handleMessage(update.message, env);
        }
        return new Response('OK', { status: 200 });
      }
      return new Response('Fariborz v4', { status: 200 });
    } catch (e) {
      console.error('Fatal:', e);
      return new Response('Error', { status: 500 });
    }
  }
};

async function handleMessage(msg, env) {
  const chatId = msg.chat.id;
  const userId = msg.from?.id;
  const name = msg.from?.first_name || '';
  let text = (msg.text || msg.caption || '').toString();
  const chatType = msg.chat.type;
  const isPrivate = chatType === 'private';
  const isGroup = !isPrivate;
  const msgId = msg.message_id;
  const hasPhoto = !!msg.photo;
  const hasVoice = !!msg.voice;

  // Rate limit (3 sec)
  const rlKey = `rl_${userId}`;
  const last = await env.CHAT_HISTORY.get(rlKey);
  if (last && (Date.now() - parseInt(last)) < 3000) return;
  await env.CHAT_HISTORY.put(rlKey, String(Date.now()));

  // ── Group: only respond when mentioned/replied/bot_name ──────
  if (isGroup) {
    const isReplyToBot = msg.reply_to_message && msg.reply_to_message.from && (msg.reply_to_message.from.username === 'nuxal_bot' || msg.reply_to_message.from.username === 'fariborz_bot');
    const mentionPatterns = ['فریبرز', 'fariborz', '@fariborz_bot', '@nuxal_bot'];
    const isMentioned = mentionPatterns.some(p => text.toLowerCase().includes(p.toLowerCase()));
    
    if (!isReplyToBot && !isMentioned && !hasVoice) return;
    
    mentionPatterns.forEach(p => {
      text = text.replace(new RegExp(p, 'gi'), '').trim();
    });
  }

  // Commands
  if (text === '/start') {
    return sendMsg(chatId, `سلام ${name}! 👋\nمن فریبرز هستم.\n\n💬 متن بفرست\n🎤 ویس بفرست\n🎨 بگو "عکس بساز"\n🔊 بگو "ویس بفرست"`, env, msgId);
  }
  if (text === '/help') {
    return sendMsg(chatId, `📋 راهنما:\n💬 هر متنی → جواب\n🎤 ویس → میفهمم\n🎨 "عکس بساز از ..." → عکس\n🔊 "ویس بفرست ..." → صدا`, env, msgId);
  }

  // Voice (STT)
  if (hasVoice) {
    return await handleVoice(msg, chatId, userId, name, env);
  }

  // Image gen
  if (text.match(/^(عکس|تصویر)\s*(بساز|بکن)/i) || text.startsWith('/generate-image')) {
    const prompt = text.replace(/^(عکس|تصویر)\s*(بساز|بکن)\s*/i, '').replace(/^\/generate-image\s*/i, '').trim();
    if (!prompt) return sendMsg(chatId, '🎨 موضوع عکس رو بگو!', env, msgId);
    return await handleImageGen(prompt, chatId, env);
  }

  // TTS
  if (text.match(/^(ویس|صدا)\s*(بفرست|بده)/i) || text.startsWith('/voice')) {
    const ttsText = text.replace(/^(ویس|صدا)\s*(بفرست|بده)\s*/i, '').replace(/^\/voice\s*/i, '').trim();
    if (!ttsText) return sendMsg(chatId, '🔊 متن رو بگو!', env, msgId);
    return await handleTTS(ttsText, chatId, env);
  }

  // ── Chat: build context from reply chain + photos ────────────
  let context = '';
  let imageB64 = null;

  // Current message photo
  if (hasPhoto) {
    imageB64 = await downloadPhoto(msg, env);
  }

  // Walk reply chain (up to 5 levels)
  let current = msg;
  let depth = 0;
  
  while (current.reply_to_message && depth < 5) {
    depth++;
    const rm = current.reply_to_message;
    const rName = rm.from?.first_name || '?';
    const rText = (rm.text || rm.caption || '').toString().substring(0, 300);
    const rHasPhoto = !!rm.photo;
    const rHasVoice = !!rm.voice;
    
    // If replied message has a photo and we don't have one yet, download it
    if (rHasPhoto && !imageB64) {
      imageB64 = await downloadPhoto(rm, env);
      context = `[عکس از ${rName}]: ${rText}\n` + context;
    } else if (rHasVoice) {
      context = `[ویس از ${rName}]: ${rText || '(پیام صوتی)'}\n` + context;
    } else {
      context = `[پیام ${rName}]: ${rText}\n` + context;
    }
    
    current = rm;
  }

  // Build final message
  let fullMsg = text || 'این عکس رو توضیح بده';
  if (context) {
    fullMsg = context + `\n[${name}]: ${fullMsg}`;
  }

  return await handleChat(fullMsg, chatId, userId, name, env, imageB64, msgId);
}

async function handleVoice(msg, chatId, userId, name, env) {
  try {
    await sendAction(chatId, 'record_voice', env);
    const file = await tgApi('getFile', { file_id: msg.voice.file_id }, env);
    if (!file?.result?.file_path) return sendMsg(chatId, '❌ خطا در دانلود صدا', env, msg.message_id);
    
    const res = await fetch(`https://api.telegram.org/file/bot${env.TELEGRAM_BOT_TOKEN}/${file.result.file_path}`);
    const buf = await res.arrayBuffer();
    const b64 = bufToB64(buf);
    
    const stt = await apiPost('/speech-to-text', { audio_base64: b64 });
    if (!stt?.text) return sendMsg(chatId, '❌ نتونستم صدا رو بفهمم', env, msg.message_id);
    
    await sendMsg(chatId, `🎤 شنیدم: "${stt.text}"`, env, msg.message_id);
    await handleChat(stt.text, chatId, userId, name, env, null, msg.message_id);
  } catch (e) {
    console.error('Voice error:', e);
    await sendMsg(chatId, '❌ خطا در پردازش صدا', env, msg.message_id);
  }
}

async function downloadPhoto(msg, env) {
  try {
    const photo = msg.photo[msg.photo.length - 1];
    const file = await tgApi('getFile', { file_id: photo.file_id }, env);
    if (!file?.result?.file_path) return null;
    
    const res = await fetch(`https://api.telegram.org/file/bot${env.TELEGRAM_BOT_TOKEN}/${file.result.file_path}`);
    const buf = await res.arrayBuffer();
    return bufToB64(buf);
  } catch (e) {
    console.error('Photo download error:', e);
    return null;
  }
}

async function handleImageGen(prompt, chatId, env) {
  try {
    await sendAction(chatId, 'upload_photo', env);
    const res = await apiPost('/generate-image', { prompt });
    if (!res?.image_base64) return sendMsg(chatId, '❌ نتونستم عکس بسازم', env);
    
    const blob = new Blob([b64ToBuf(res.image_base64)], { type: 'image/jpeg' });
    const fd = new FormData();
    fd.append('chat_id', String(chatId));
    fd.append('photo', blob, 'image.jpg');
    fd.append('caption', `🎨 ${prompt}`);
    
    await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendPhoto`, { method: 'POST', body: fd });
  } catch (e) {
    await sendMsg(chatId, '❌ خطا در ساخت عکس', env);
  }
}

async function handleTTS(text, chatId, env) {
  try {
    await sendAction(chatId, 'record_voice', env);
    const res = await apiPost('/text-to-speech', { text });
    if (!res?.audio_base64) return sendMsg(chatId, '❌ نتونستم صدا بسازم', env);
    
    const blob = new Blob([b64ToBuf(res.audio_base64)], { type: 'audio/mpeg' });
    const fd = new FormData();
    fd.append('chat_id', String(chatId));
    fd.append('voice', blob, 'voice.mp3');
    
    await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendVoice`, { method: 'POST', body: fd });
  } catch (e) {
    await sendMsg(chatId, '❌ خطا در تولید صدا', env);
  }
}

async function handleChat(text, chatId, userId, name, env, imageB64, replyTo) {
  try {
    await sendAction(chatId, 'typing', env);
    
    const hKey = `hist_${chatId}`;
    const hJson = await env.CHAT_HISTORY.get(hKey);
    let history = hJson ? JSON.parse(hJson) : [];
    
    const body = { message: text, user_id: String(userId), user_name: name, history: history };
    if (imageB64) body.image_base64 = imageB64;
    
    const res = await apiPost('/chat', body);
    if (res?.error) return sendMsg(chatId, `⚠️ ${res.error}`, env, replyTo);
    
    const reply = res?.response || 'پاسخی دریافت نشد';
    await sendMsg(chatId, reply, env, replyTo);
    
    history.push({ role: 'user', text: text.substring(0, 500), timestamp: Date.now() });
    history.push({ role: 'assistant', text: reply.substring(0, 500), timestamp: Date.now() });
    if (history.length > 20) history = history.slice(-20);
    await env.CHAT_HISTORY.put(hKey, JSON.stringify(history));
  } catch (e) {
    console.error('Chat error:', e);
    await sendMsg(chatId, '❌ خطا در پردازش پیام', env, replyTo);
  }
}

// ── Helpers ────────────────────────────────────────────────────────
async function sendMsg(chatId, text, env, replyTo) {
  const body = { chat_id: chatId, text };
  if (replyTo) body.reply_to_message_id = replyTo;
  await tgApi('sendMessage', body, env);
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

async function apiPost(path, body) {
  try {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: API_SECRET, ...body })
    });
    const data = await res.json();
    if (data.error) return { error: data.error };
    return data;
  } catch (e) {
    console.error(`API ${path}:`, e);
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
