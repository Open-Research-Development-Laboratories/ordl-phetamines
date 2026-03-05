#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { decide } = require('../policy/engine');

const scenariosPath = path.join(__dirname, 'policy-scenarios.json');
const data = JSON.parse(fs.readFileSync(scenariosPath, 'utf8'));

let pass = 0;
let fail = 0;
for (const s of data.scenarios) {
  const out = decide(s.input);
  const ok = out.decision === s.expect.decision && out.ruleId === s.expect.ruleId;
  if (ok) {
    pass += 1;
    console.log(`PASS ${s.id} ${s.name} -> ${out.decision}/${out.ruleId}`);
  } else {
    fail += 1;
    console.log(`FAIL ${s.id} ${s.name}`);
    console.log(`  expected: ${s.expect.decision}/${s.expect.ruleId}`);
    console.log(`  actual:   ${out.decision}/${out.ruleId}`);
  }
}

console.log(`\nResult: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
