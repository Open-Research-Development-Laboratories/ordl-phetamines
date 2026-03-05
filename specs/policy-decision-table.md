# Policy Decision Table (Universal Outbound Gate)

## Priority
Evaluate top to bottom. First terminal match wins.

| Priority | Condition | Decision | Rule ID |
|---|---|---|---|
| 1 | runtime_state.mode == frozen and destination not in emergency_allowlist | deny | G-001 |
| 2 | quiet_keyword_active == true and explicit_resume == false | deny | G-002 |
| 3 | channel/group/public and direct_request == false and was_mentioned == false | deny | G-003 |
| 4 | contains_sensitive == true and destination.scope in [group, public] | deny | DLP-001 |
| 5 | destination on denylist | deny | DST-001 |
| 6 | rate limit exceeded for actor/channel/window | deny | RL-001 |
| 7 | risk_level in [high, critical] and actor.role lacks high_risk_send | hold_for_approval | A-001 |
| 8 | intent == proactive and mode == quiet | hold_for_approval | A-002 |
| 9 | unknown recipient and allowlist_hit == false and action.type == send | hold_for_approval | A-003 |
| 10 | explicit human instruction from authorized controller (Winsock) | allow | AUTH-001 |
| 11 | direct_request == true and no deny condition matched | allow | OK-001 |
| 12 | default | deny | G-999 |

## Notes
- `AUTH-001` still requires DLP checks to pass.
- Any missing required field in event schema is terminal deny (`G-000`).
- Model judge output is non-authoritative and cannot flip deny to allow.
