#!/usr/bin/env node

function decide(event) {
  const reasons = [];
  const mode = event?.runtime_state?.mode;
  const ctx = event?.context || {};
  const dest = event?.destination || {};
  const action = event?.action || {};
  const payload = event?.payload || {};
  const actor = event?.actor || {};

  // G-000 schema guard (minimal runtime check)
  const required = [event?.event_id, event?.timestamp, event?.channel, action?.type, action?.intent, dest?.scope];
  if (required.some((v) => v === undefined || v === null || v === "")) {
    return { decision: "deny", ruleId: "G-000", reason: "missing required fields" };
  }

  // G-001 frozen mode
  if (mode === "frozen" && !dest?.emergency_allowlist_hit) {
    return { decision: "deny", ruleId: "G-001", reason: "frozen mode" };
  }

  // G-002 quiet keyword active without explicit resume
  if (ctx?.quiet_keyword_active === true && ctx?.explicit_resume !== true) {
    return { decision: "deny", ruleId: "G-002", reason: "quiet lock active" };
  }

  // G-003 group/public chatter without direct request or mention
  const groupLike = dest?.scope === "group" || dest?.scope === "public";
  if (groupLike && ctx?.direct_request !== true && ctx?.was_mentioned !== true) {
    return { decision: "deny", ruleId: "G-003", reason: "no reply trigger in group/public" };
  }

  // DLP-001 sensitive -> group/public
  if (payload?.contains_sensitive === true && groupLike) {
    return { decision: "deny", ruleId: "DLP-001", reason: "sensitive content to group/public" };
  }

  // DST-001 denylist
  if (dest?.denylist_hit === true) {
    return { decision: "deny", ruleId: "DST-001", reason: "destination denylist" };
  }

  // RL-001
  if (event?.rate_limit_exceeded === true) {
    return { decision: "deny", ruleId: "RL-001", reason: "rate limit exceeded" };
  }

  // A-001 high-risk no privilege
  if (["high", "critical"].includes(action?.risk_level) && actor?.high_risk_send !== true) {
    return { decision: "hold_for_approval", ruleId: "A-001", reason: "high-risk requires approval" };
  }

  // A-002 proactive in quiet mode
  if (action?.intent === "proactive" && mode === "quiet") {
    return { decision: "hold_for_approval", ruleId: "A-002", reason: "proactive in quiet mode" };
  }

  // A-003 unknown recipient send
  if (dest?.allowlist_hit === false && action?.type === "send") {
    return { decision: "hold_for_approval", ruleId: "A-003", reason: "unknown recipient" };
  }

  // AUTH-001 explicit authorized controller command
  if (actor?.role === "controller" && ctx?.direct_request === true) {
    return { decision: "allow", ruleId: "AUTH-001", reason: "authorized controller command" };
  }

  // OK-001 direct request
  if (ctx?.direct_request === true) {
    return { decision: "allow", ruleId: "OK-001", reason: "direct request" };
  }

  return { decision: "deny", ruleId: "G-999", reason: "default deny" };
}

module.exports = { decide };

if (require.main === module) {
  const fs = require("fs");
  const path = process.argv[2];
  if (!path) {
    console.error("Usage: node policy/engine.js <event.json>");
    process.exit(2);
  }
  const event = JSON.parse(fs.readFileSync(path, "utf8"));
  const out = decide(event);
  process.stdout.write(JSON.stringify(out, null, 2) + "\n");
}
