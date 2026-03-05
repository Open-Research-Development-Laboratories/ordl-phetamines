#!/usr/bin/env node
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { decide } = require('./engine');
const { sendDiscordAlert, sendEmailAlert } = require('./alerts');

const PORT = Number(process.env.POLICY_GATEWAY_PORT || 8789);
const SECRET = process.env.POLICY_GATEWAY_SECRET || 'change-me';
const LOG_PATH = process.env.POLICY_GATEWAY_LOG || path.join(__dirname, 'audit.log');
const STATUS_PATH = process.env.POLICY_STATUS_PATH || path.join(__dirname, 'status.json');
const QUEUE_PATH = process.env.POLICY_QUEUE_PATH || path.join(__dirname, 'blocked-queue.jsonl');

const ALERT_DISCORD_TARGET = process.env.POLICY_ALERT_DISCORD_TARGET || 'channel:1379869405164343353';
const ALERT_EMAIL_TO = process.env.POLICY_ALERT_EMAIL_TO || '';

function readJson(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (c) => {
      body += c;
      if (body.length > 2_000_000) reject(new Error('payload too large'));
    });
    req.on('end', () => {
      try { resolve(body ? JSON.parse(body) : {}); } catch (e) { reject(e); }
    });
    req.on('error', reject);
  });
}

function signDecision(payload) {
  const h = crypto.createHmac('sha256', SECRET);
  h.update(JSON.stringify(payload));
  return h.digest('hex');
}

function writeAudit(row) {
  fs.appendFileSync(LOG_PATH, JSON.stringify(row) + '\n');
}

function writeStatus(status) {
  fs.writeFileSync(STATUS_PATH, JSON.stringify(status, null, 2));
}

function enqueueBlocked(row) {
  fs.appendFileSync(QUEUE_PATH, JSON.stringify(row) + '\n');
}

function send(res, code, obj) {
  res.writeHead(code, { 'content-type': 'application/json' });
  res.end(JSON.stringify(obj));
}

function short(str, n = 160) {
  const s = String(str || '');
  return s.length > n ? s.slice(0, n) + '…' : s;
}

async function alertOnBlock(event, out) {
  const actor = event?.actor?.actor_id || 'unknown-actor';
  const target = event?.destination?.target || 'unknown-target';
  const text = short(event?.payload?.text || '');
  const msg = [
    'POLICY BLOCKED',
    `decision=${out.decision}`,
    `rule=${out.ruleId}`,
    `why=${out.reason}`,
    `who=${actor}`,
    `target=${target}`,
    `what=${text}`,
    `event=${out.event_id}`
  ].join(' | ');

  const discord = await sendDiscordAlert({ target: ALERT_DISCORD_TARGET, message: msg });
  let email = { ok: false, skipped: true, reason: 'not configured' };
  if (ALERT_EMAIL_TO) {
    email = await sendEmailAlert({
      to: ALERT_EMAIL_TO,
      subject: `[POLICY] Blocked ${out.ruleId}`,
      body: msg
    });
  }

  writeAudit({ kind: 'alert', at: new Date().toISOString(), discord, email, event_id: out.event_id, ruleId: out.ruleId });
}

function nowStatus(mode, last) {
  return {
    updatedAt: new Date().toISOString(),
    ui: {
      color: mode,
      banner: mode === 'red' ? 'POLICY BLOCK ACTIVE' : mode === 'yellow' ? 'POLICY HOLD QUEUE' : 'POLICY OK'
    },
    last
  };
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === 'GET' && req.url === '/health') {
      return send(res, 200, { ok: true, service: 'policy-gateway' });
    }

    if (req.method === 'GET' && req.url === '/status') {
      if (!fs.existsSync(STATUS_PATH)) writeStatus(nowStatus('green', null));
      const status = JSON.parse(fs.readFileSync(STATUS_PATH, 'utf8'));
      return send(res, 200, status);
    }

    if (req.method === 'POST' && req.url === '/reevaluate') {
      const payload = await readJson(req);
      const event = payload?.event;
      if (!event) return send(res, 400, { ok: false, error: 'missing event' });
      const decision = decide(event);
      const out = {
        event_id: event?.event_id || null,
        timestamp: new Date().toISOString(),
        decision: decision.decision,
        ruleId: decision.ruleId,
        reason: decision.reason,
        policy_version: 'v1',
        reevaluated: true
      };
      out.signature = signDecision(out);
      writeAudit({ kind: 'reevaluate', ...out });
      if (out.decision === 'allow') writeStatus(nowStatus('green', out));
      else if (out.decision === 'hold_for_approval') writeStatus(nowStatus('yellow', out));
      else writeStatus(nowStatus('red', out));
      return send(res, 200, out);
    }

    if (req.method === 'POST' && req.url === '/decide') {
      const event = await readJson(req);
      const decision = decide(event);
      const out = {
        event_id: event?.event_id || null,
        timestamp: new Date().toISOString(),
        decision: decision.decision,
        ruleId: decision.ruleId,
        reason: decision.reason,
        policy_version: 'v1'
      };
      out.signature = signDecision(out);
      writeAudit({ kind: 'decision', ...out, channel: event?.channel, target: event?.destination?.target });

      if (out.decision === 'allow') {
        writeStatus(nowStatus('green', out));
      } else if (out.decision === 'hold_for_approval') {
        writeStatus(nowStatus('yellow', out));
        enqueueBlocked({ event, out });
        await alertOnBlock(event, out);
      } else {
        writeStatus(nowStatus('red', out));
        enqueueBlocked({ event, out });
        await alertOnBlock(event, out);
      }

      return send(res, 200, out);
    }

    return send(res, 404, { ok: false, error: 'not_found' });
  } catch (err) {
    writeAudit({ kind: 'error', at: new Date().toISOString(), error: String(err?.message || err) });
    writeStatus(nowStatus('red', { decision: 'deny', ruleId: 'SYS-ERR', reason: String(err?.message || err) }));
    return send(res, 500, { ok: false, error: 'internal_error', detail: String(err?.message || err) });
  }
});

if (!fs.existsSync(STATUS_PATH)) writeStatus(nowStatus('green', null));
server.listen(PORT, '127.0.0.1', () => {
  console.log(`policy-gateway listening on http://127.0.0.1:${PORT}`);
});
