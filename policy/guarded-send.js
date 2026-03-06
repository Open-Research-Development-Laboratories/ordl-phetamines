#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const http = require('http');
const { execFileSync } = require('child_process');

function postJson(url, payload) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const req = http.request({
      hostname: u.hostname,
      port: u.port,
      path: u.pathname,
      method: 'POST',
      headers: { 'content-type': 'application/json' }
    }, (res) => {
      let body = '';
      res.on('data', (c) => body += c);
      res.on('end', () => {
        try { resolve(JSON.parse(body || '{}')); } catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.write(JSON.stringify(payload));
    req.end();
  });
}

async function main() {
  const inputPath = process.argv[2];
  if (!inputPath) {
    console.error('usage: node policy/guarded-send.js <event.json>');
    process.exit(2);
  }
  const event = JSON.parse(fs.readFileSync(path.resolve(inputPath), 'utf8'));
  const gateway = process.env.POLICY_GATEWAY_URL || 'http://127.0.0.1:8789/decide';
  const out = await postJson(gateway, event);

  if (out.decision !== 'allow') {
    console.error(`blocked: ${out.decision} ${out.ruleId} ${out.reason}`);
    process.exit(10);
  }

  const channel = event.channel;
  const target = event.destination?.target;
  const msg = event.payload?.text || '';
  if (!channel || !target || !msg) {
    console.error('missing channel/target/message in event');
    process.exit(3);
  }

  // Operator-facing dispatch path. This is for local controlled automation.
  const result = execFileSync('ordlctl', ['message', 'send', '--channel', channel, '--target', target, '--message', msg], { encoding: 'utf8' });
  process.stdout.write(result);
}

main().catch((e) => {
  console.error(String(e?.stack || e));
  process.exit(1);
});
