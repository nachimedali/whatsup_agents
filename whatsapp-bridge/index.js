/**
 * AgentFlow WhatsApp Bridge — Group-aware version
 *
 * Behaviour:
 *  - DM messages: ignored (bridge no longer processes 1-on-1 DMs by default)
 *  - Group messages: forwarded to FastAPI only if the group is in the allowed list
 *    (FastAPI decides; the bridge just forwards everything from @g.us chats)
 *
 * Express endpoints (consumed by FastAPI):
 *  POST /send        — send a message to a chat or group ID
 *  GET  /groups      — list all WhatsApp groups the bot is currently in
 *  GET  /health      — connectivity check
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const axios = require('axios');

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';
const PORT = parseInt(process.env.PORT || '3001');

// ── Express server ──────────────────────────────────────────────────────────

const app = express();
app.use(express.json());

// Allow cross-origin requests (FastAPI backend + local dashboard dev server)
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.sendStatus(200);
  next();
});

let waClient = null;

/** Send a message to any chat ID (DM or group). Called by FastAPI after agent replies. */
app.post('/send', async (req, res) => {
  const { sender_id, message } = req.body;
  if (!waClient) {
    return res.status(503).json({ error: 'WhatsApp not connected' });
  }
  try {
    await waClient.sendMessage(sender_id, message);
    res.json({ ok: true });
  } catch (err) {
    console.error('[Bridge] Send error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

/** Return all groups the bot is a member of. FastAPI syncs these into its DB. */
app.get('/groups', async (req, res) => {
  if (!waClient) {
    return res.status(503).json({ error: 'WhatsApp not connected' });
  }
  try {
    const chats = await waClient.getChats();
    const groups = chats
      .filter(c => c.isGroup)
      .map(c => ({
        id: c.id._serialized,   // e.g. "120363000000000000@g.us"
        name: c.name,
        participants: c.participants?.length ?? 0,
      }));
    res.json({ groups });
  } catch (err) {
    console.error('[Bridge] /groups error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: waClient ? 'connected' : 'connecting' });
});

app.listen(PORT, () => {
  console.log(`[Bridge] HTTP server listening on port ${PORT}`);
});

// ── WhatsApp client ─────────────────────────────────────────────────────────

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: './.wa-session' }),
  puppeteer: {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
});

client.on('qr', (qr) => {
  console.log('\n[Bridge] Scan this QR code with WhatsApp:\n');
  qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
  console.log('[Bridge] WhatsApp connected ✓');
  console.log('[Bridge] Only group messages will be processed.');
  console.log('[Bridge] Use the dashboard to enable specific groups.');
  waClient = client;
});

client.on('disconnected', (reason) => {
  console.log('[Bridge] WhatsApp disconnected:', reason);
  waClient = null;
});

client.on('message_create', async (msg) => {
  // Skip status broadcasts and self-messages
  console.log("--- Message ----")
  console.log(msg)
  console.log(msg.from)
  if (msg.from === 'status@broadcast') return;

  const isGroup = msg.from.endsWith('@g.us');

  // ── DM messages: skip ────────────────────────────────────────────────────
  // The bridge now only handles group messages. Remove this block if you also
  // want to handle DMs on the same number.
  if (!isGroup && !msg.fromMe) return;

  // ── Group message ─────────────────────────────────────────────────────────
  const groupId = msg.from;                  // e.g. "120363...@g.us"
  const authorId = msg.author || msg.from;   // who sent it inside the group

  // Only process messages that @mention an agent (start with @something)
  // This avoids noise from unrelated group chatter.
  const body = msg.body.trim();
  if (!body.startsWith('@')) {
    return;  // ignore non-agent messages silently
  }

  // Resolve the sender's display name
  let senderName = authorId;
  try {
    const contact = await waClient.getContactById(authorId);
    senderName = contact.pushname || contact.name || authorId;
  } catch {}

  const chat = await msg.getChat();
  const groupName = chat.name || groupId;

  console.log(`[Bridge] Group "${groupName}" | ${senderName}: ${body.substring(0, 80)}`);

  try {
    await axios.post(`${FASTAPI_URL}/api/messages/incoming`, {
      sender_id: authorId,       // the individual author
      sender_name: senderName,
      message: body,
      channel: 'whatsapp_group',
      group_id: groupId,         // the group — FastAPI uses this for routing & reply target
    });
  } catch (err) {
    console.error('[Bridge] Failed to forward to FastAPI:', err.message);
    try {
      await waClient.sendMessage(groupId,
        '⚠️ Agent system is temporarily unavailable. Please try again.'
      );
    } catch {}
  }
});

client.initialize();
console.log('[Bridge] Initializing WhatsApp client...');
