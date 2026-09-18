---
name: whatsapp-railway-bridge
description: Build and deploy a WhatsApp-to-Telegram message bridge using whatsapp-web.js, deployed on Railway with persistent auth. Use this skill whenever the user wants to connect WhatsApp to Telegram, forward WhatsApp group messages, build a WhatsApp bot deployed to the cloud, or work with whatsapp-web.js on Railway/Docker. Also trigger when user mentions WhatsApp automation, WhatsApp bridge, or deploying Puppeteer-based apps to Railway.
---

# WhatsApp-Telegram Bridge on Railway

Build a bridge that listens to a WhatsApp group and forwards messages (text, images, videos, documents) to a Telegram channel/group. Deployed on Railway with persistent authentication.

## Architecture Overview

```
WhatsApp Group → whatsapp-web.js (Puppeteer) → Node.js Bridge → Telegram Bot API → Telegram Channel
```

The bridge runs as a Node.js process with a headless Chrome instance (via Puppeteer) that connects to WhatsApp Web. It listens for messages in a specific group and forwards them to Telegram.

## Project Structure

```
whatsapp-telegram-bridge/
├── index.js          # Main bridge logic
├── package.json
├── Dockerfile        # Railway/Docker deployment
├── .env              # Local config (not committed)
└── .wwebjs_auth/     # WhatsApp session (persisted via Railway volume)
```

Templates for all files are in `templates/` directory of this skill. Copy them as a starting point.

## Critical Lessons Learned (from real deployment)

### 1. Puppeteer Config for Railway/Linux

Railway runs Linux containers. Chrome needs specific flags:

```js
puppeteer: {
  headless: true,
  executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
  args: [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--single-process'
  ],
}
```

- `PUPPETEER_EXECUTABLE_PATH` should be `/usr/bin/chromium` in Docker
- `PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true` in Docker to use system Chromium

### 2. QR Code Handling

Terminal QR codes don't render properly in most environments (Windows terminals, Railway logs). Solution: **send the QR as an image to Telegram**.

```js
const QRCode = require('qrcode');

client.on('qr', async (qr) => {
  const qrBuffer = await QRCode.toBuffer(qr, { width: 400 });
  await telegramSendPhoto(qrBuffer, 'Scan this QR with WhatsApp');
});
```

Use the `qrcode` package (NOT `qrcode-terminal`) for image generation. If both are installed, there's a naming conflict - use separate imports.

### 3. Chrome Lock File Cleanup (CRITICAL)

After container restarts on Railway, Chrome lock files persist on the volume and prevent Chrome from launching with error: "The profile appears to be in use by another Chromium process".

**Must clean these on every startup:**

```js
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
```

Call this BEFORE `client.initialize()`.

### 4. WhatsApp Formatting to Telegram HTML

WhatsApp uses markdown-like formatting, Telegram uses HTML. Convert in ALL send functions (text, photo captions, video captions, document captions):

```js
function convertFormat(text) {
  text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  text = text.replace(/\*(.*?)\*/g, '<b>$1</b>');
  text = text.replace(/_(.*?)_/g, '<i>$1</i>');
  text = text.replace(/~(.*?)~/g, '<s>$1</s>');
  text = text.replace(/```(.*?)```/gs, '<code>$1</code>');
  return text;
}
```

**Apply `convertFormat()` at the top of EVERY Telegram send function** - not just `sendText` but also `sendPhoto`, `sendVideo`, `sendDocument`. This is easy to miss and causes asterisks to show up in Telegram messages that have media.

### 5. Hebrew Group Name Matching

Hebrew group names may have invisible characters or slight variations. Use `includes()` instead of exact match:

```js
// BAD - breaks with Hebrew names
if (chat.name !== WHATSAPP_GROUP_NAME) return;

// GOOD - resilient to minor differences
if (!chat.name.includes(WHATSAPP_GROUP_NAME)) return;
```

Also add debug logging to discover the exact group name:

```js
console.log(`[DEBUG] Message from: ${msg.fromMe ? 'ME' : 'OTHER'} | Group: ${chat.isGroup} | Chat name: "${chat.name}"`);
```

### 6. Error Handling (Prevents Crash Loops)

whatsapp-web.js throws "Execution context was destroyed" errors during WhatsApp Web page navigation. These are non-fatal but will crash the process if uncaught:

```js
process.on('unhandledRejection', (err) => {
  console.error('Unhandled rejection (not crashing):', err.message);
});
process.on('uncaughtException', (err) => {
  console.error('Uncaught exception (not crashing):', err.message);
});
```

Also wrap the message handler in try/catch, and add auto-reconnect on disconnect:

```js
client.on('disconnected', (reason) => {
  console.log('Disconnected:', reason);
  setTimeout(() => client.initialize(), 5000);
});
```

### 7. Railway Deployment

#### Dockerfile Requirements

```dockerfile
FROM node:20-slim

RUN apt-get update && apt-get install -y \
    chromium \
    fonts-noto \
    fonts-noto-color-emoji \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
```

- `fonts-noto` is required for Hebrew/Arabic text rendering
- `fonts-noto-color-emoji` for emoji support

#### Railway Volume

Mount a volume at `/app/.wwebjs_auth` to persist the WhatsApp session across deploys. Without this, you'd need to scan the QR code on every deploy.

#### Health Check Server

Railway requires a listening port. Add a minimal HTTP server:

```js
const server = http.createServer((req, res) => {
  res.writeHead(200);
  res.end('Bridge is running');
});
server.listen(process.env.PORT || 3000);
```

#### Environment Variables on Railway

```
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=@your-channel-or-chat-id
TELEGRAM_ADMIN_CHAT_ID=your-personal-chat-id  (for QR codes)
WHATSAPP_GROUP_NAME=exact group name
PORT=3000
```

### 8. Media Handling

Download media from WhatsApp and forward to Telegram based on MIME type:

```js
if (msg.hasMedia) {
  const media = await msg.downloadMedia();
  const buffer = Buffer.from(media.data, 'base64');

  if (media.mimetype.startsWith('image/')) {
    await telegramSendPhoto(buffer, msg.body);
  } else if (media.mimetype.startsWith('video/')) {
    await telegramSendVideo(buffer, msg.body);
  } else {
    await telegramSendDocument(buffer, media.filename, msg.body);
  }
}
```

### 9. `message_create` vs `message`

Use `message_create` event to capture messages YOU send (not just incoming messages). Filter with `msg.fromMe`:

```js
client.on('message_create', async (msg) => {
  if (!msg.fromMe) return;  // only forward your own messages
  // ...
});
```

If you want to forward ALL group messages, remove the `fromMe` filter.

### 10. Web Version Cache

WhatsApp Web frequently updates, which can break whatsapp-web.js. Use a remote cache:

```js
webVersionCache: {
  type: 'remote',
  remotePath: 'https://raw.githubusercontent.com/nicecaydev/nicecaydev.github.io/refs/heads/main/',
},
```

## Setup Checklist

1. Create Telegram bot via @BotFather, get token
2. Add bot to your Telegram channel/group as admin
3. Get chat ID (use @userinfobot or `@channelname` for public channels)
4. Copy template files from this skill's `templates/` directory
5. Set up `.env` with your credentials
6. Run locally first: `npm install && npm start`
7. Scan QR code (sent to Telegram or opens locally)
8. Test by sending a message in the WhatsApp group
9. Create GitHub repo and push
10. Deploy to Railway with Dockerfile, add volume at `/app/.wwebjs_auth`
11. Set environment variables on Railway
12. Scan QR one more time from Telegram after first deploy

## Dependencies

```json
{
  "dotenv": "^16.4.5",
  "qrcode": "^1.5.4",
  "whatsapp-web.js": "^1.26.0"
}
```

Note: `qrcode-terminal` is NOT needed. Use `qrcode` for image generation.
