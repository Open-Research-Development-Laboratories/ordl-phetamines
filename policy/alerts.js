#!/usr/bin/env node
const { execFile } = require('child_process');

function run(cmd, args) {
  return new Promise((resolve) => {
    execFile(cmd, args, { timeout: 15000 }, (err, stdout, stderr) => {
      resolve({ ok: !err, err: err ? String(err.message || err) : null, stdout: String(stdout || ''), stderr: String(stderr || '') });
    });
  });
}

async function sendDiscordAlert(params) {
  const { target, message } = params;
  if (!target) return { ok: false, skipped: true, reason: 'no target' };
  return run('ordlctl', ['message', 'send', '--channel', 'discord', '--target', target, '--message', message]);
}

async function sendEmailAlert(params) {
  // Uses local sendmail if available.
  const { to, subject, body } = params;
  if (!to) return { ok: false, skipped: true, reason: 'no to' };
  const script = `To: ${to}\nSubject: ${subject}\nContent-Type: text/plain; charset=UTF-8\n\n${body}\n`;
  return new Promise((resolve) => {
    const p = require('child_process').spawn('sendmail', ['-t'], { stdio: ['pipe', 'pipe', 'pipe'] });
    let stderr = '';
    p.stderr.on('data', (d) => stderr += d.toString());
    p.on('close', (code) => resolve({ ok: code === 0, code, stderr }));
    p.on('error', (e) => resolve({ ok: false, err: String(e.message || e) }));
    p.stdin.write(script);
    p.stdin.end();
  });
}

module.exports = { sendDiscordAlert, sendEmailAlert };
