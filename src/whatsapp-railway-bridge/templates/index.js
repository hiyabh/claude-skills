const { Client, LocalAuth } = require('whatsapp-web.js');
const QRCode = require('qrcode');
const http = require('http');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// --- Clean up stale Chrome lock files from previous runs ---
// Without this, Railway containers crash with "profile in use" error after restart
const authDir = './.wwebjs_auth';
function cleanLockFiles(dir) {
  if (!fs.existsSync(dir)) return;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) cleanLockFiles(full);
    else if (['SingletonLock', 'SingletonCookie', 'SingletonSocket'].includes(entry.name)) {
      fs.unlinkSync(full);
      console.log(`Cleaned lock file: ${full}`);
    }
  }
}

// --- Config ---
const WHATSAPP_GROUP_NAME = process.env.WHATSAPP_GROUP_NAME || 'YOUR_GROUP_NAME';
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;
const TELEGRAM_ADMIN_CHAT_ID = process.env.TELEGRAM_ADMIN_CHAT_ID;
const PORT = process.env.PORT || 3000;

if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
  console.error('Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env');
  process.exit(1);
}

const TELEGRAM_API = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}`;

let whatsappStatus = 'initializing';

// --- Health check server (required by Railway) ---
const server = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', whatsapp: whatsappStatus }));
  } else {
    res.writeHead(200);
    res.end('WhatsApp-Telegram Bridge is running');
  }
});
server.listen(PORT, () => console.log(`Health check on port ${PORT}`));

// --- WhatsApp to Telegram format converter ---
// IMPORTANT: Apply this in ALL send functions (text, photo, video, document)
function convertFormat(text) {
  if (!text) return '';
  text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  text = text.replace(/\*(.*?)\*/g, '<b>$1</b>');
  text = text.replace(/_(.*?)_/g, '<i>$1</i>');
  text = text.replace(/~(.*?)~/g, '<s>$1</s>');
  text = text.replace(/```(.*?)```/gs, '<code>$1</code>');
  return text;
}

// --- Telegram helpers ---
async function telegramSendText(text, chatId = TELEGRAM_CHAT_ID) {
  text = convertFormat(text);
  const res = await fetch(`${TELEGRAM_API}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'HTML',
      disable_web_page_preview: false,
    }),
  });
  if (!res.ok) console.error('Telegram sendMessage error:', await res.text());
  return res;
}

async function telegramSendPhoto(photoBuffer, caption = '', chatId = TELEGRAM_CHAT_ID) {
  caption = convertFormat(caption);
  const formData = new FormData();
  formData.append('chat_id', chatId);
  formData.append('photo', new Blob([photoBuffer]), 'photo.jpg');
  if (caption) {
    formData.append('caption', caption);
    formData.append('parse_mode', 'HTML');
  }
  const res = await fetch(`${TELEGRAM_API}/sendPhoto`, { method: 'POST', body: formData });
  if (!res.ok) console.error('Telegram sendPhoto error:', await res.text());
  return res;
}

async function telegramSendDocument(docBuffer, filename, caption = '') {
  caption = convertFormat(caption);
  const formData = new FormData();
  formData.append('chat_id', TELEGRAM_CHAT_ID);
  formData.append('document', new Blob([docBuffer]), filename);
  if (caption) {
    formData.append('caption', caption);
    formData.append('parse_mode', 'HTML');
  }
  const res = await fetch(`${TELEGRAM_API}/sendDocument`, { method: 'POST', body: formData });
  if (!res.ok) console.error('Telegram sendDocument error:', await res.text());
  return res;
}

async function telegramSendVideo(videoBuffer, caption = '') {
  caption = convertFormat(caption);
  const formData = new FormData();
  formData.append('chat_id', TELEGRAM_CHAT_ID);
  formData.append('video', new Blob([videoBuffer]), 'video.mp4');
  if (caption) {
    formData.append('caption', caption);
    formData.append('parse_mode', 'HTML');
  }
  const res = await fetch(`${TELEGRAM_API}/sendVideo`, { method: 'POST', body: formData });
  if (!res.ok) console.error('Telegram sendVideo error:', await res.text());
  return res;
}

// --- WhatsApp Client ---
const client = new Client({
  authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
  webVersionCache: {
    type: 'remote',
    remotePath: 'https://raw.githubusercontent.com/nicecaydev/nicecaydev.github.io/refs/heads/main/',
  },
  puppeteer: {
    headless: true,
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--single-process'],
  },
});

client.on('qr', async (qr) => {
  console.log('QR code received, sending to Telegram...');
  whatsappStatus = 'waiting_for_qr_scan';

  // Send QR as image to Telegram (terminal QR doesn't render properly)
  const qrBuffer = await QRCode.toBuffer(qr, { width: 400 });
  const adminChat = TELEGRAM_ADMIN_CHAT_ID || TELEGRAM_CHAT_ID;
  await telegramSendPhoto(qrBuffer, 'Scan this QR with WhatsApp:\nSettings > Linked Devices > Link a Device', adminChat);
  console.log('QR sent to Telegram! Waiting for scan...');

  // Also try to open locally (works on Windows dev machine, silently fails on server)
  try {
    const qrPath = path.join(__dirname, 'qr-code.png');
    await QRCode.toFile(qrPath, qr, { width: 300 });
    require('child_process').exec(`start "" "${qrPath}"`);
  } catch (e) { /* ignore on server */ }
});

client.on('ready', () => {
  whatsappStatus = 'connected';
  console.log(`WhatsApp connected! Listening to: "${WHATSAPP_GROUP_NAME}"`);
  const adminChat = TELEGRAM_ADMIN_CHAT_ID || TELEGRAM_CHAT_ID;
  telegramSendText(`WhatsApp Bridge connected!\nListening to: "${WHATSAPP_GROUP_NAME}"`, adminChat);
});

client.on('authenticated', () => {
  whatsappStatus = 'authenticated';
  console.log('WhatsApp authenticated');
});

client.on('auth_failure', (msg) => {
  whatsappStatus = 'auth_failed';
  console.error('Auth failed:', msg);
});

client.on('disconnected', (reason) => {
  whatsappStatus = 'disconnected';
  console.log('Disconnected:', reason);
  setTimeout(() => client.initialize(), 5000);
});

// --- Main message handler ---
// Uses message_create to capture YOUR messages (not just incoming)
client.on('message_create', async (msg) => {
  try {
    const chat = await msg.getChat();

    // Debug logging - helps discover exact group names
    console.log(`[DEBUG] Message from: ${msg.fromMe ? 'ME' : 'OTHER'} | Group: ${chat.isGroup} | Chat name: "${chat.name}" | Body: "${msg.body?.substring(0, 50)}"`);

    // Filter: only your messages in the target group
    if (!msg.fromMe) return;
    if (!chat.isGroup || chat.name !== WHATSAPP_GROUP_NAME) return;

    console.log(`[${new Date().toLocaleTimeString()}] Forwarding message to Telegram...`);

    if (msg.hasMedia) {
      const media = await msg.downloadMedia();
      if (!media) {
        if (msg.body) await telegramSendText(msg.body);
        return;
      }

      const buffer = Buffer.from(media.data, 'base64');
      const caption = msg.body || '';

      if (media.mimetype.startsWith('image/')) {
        await telegramSendPhoto(buffer, caption);
      } else if (media.mimetype.startsWith('video/')) {
        await telegramSendVideo(buffer, caption);
      } else {
        const filename = media.filename || `file.${media.mimetype.split('/')[1] || 'bin'}`;
        await telegramSendDocument(buffer, filename, caption);
      }
    } else if (msg.body) {
      await telegramSendText(msg.body);
    }

    console.log('  Forwarded!\n');
  } catch (error) {
    console.error('Error:', error.message);
  }
});

// --- Prevent uncaught errors from crashing the process ---
// whatsapp-web.js throws "Execution context was destroyed" during page navigation
process.on('unhandledRejection', (err) => {
  console.error('Unhandled rejection (not crashing):', err.message);
});
process.on('uncaughtException', (err) => {
  console.error('Uncaught exception (not crashing):', err.message);
});

// --- Start with retry ---
async function start() {
  try {
    console.log('Starting WhatsApp-Telegram Bridge...');
    cleanLockFiles(authDir);
    await client.initialize();
  } catch (err) {
    console.error('Init failed:', err.message);
    console.log('Retrying in 10 seconds...');
    setTimeout(start, 10000);
  }
}
start();
