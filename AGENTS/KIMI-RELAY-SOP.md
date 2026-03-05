# Kimi Relay SOP

## Goal
Reliable file relay + predictable output every session.

## Session Startup (2 minutes)
1. Use one dedicated Kimi thread for this workflow.
2. Send this control prompt:

"Acknowledge every upload by exact filename. Then return output in this order: Summary, Risks, Action List, Open Questions. If anything is missing, ask specifically for the missing item."

3. Send relay marker file: `kimi-link-test.txt`.
4. Ask: "Quote line 1 from kimi-link-test.txt."

Pass condition: exact line is quoted.

## File Intake Rule
For every upload batch, ask:
"List every filename you can see in this thread right now."

Pass condition: full expected list appears.

## Work Rule
For each task, use this message shape:
- Task objective
- Inputs to use (filenames)
- Required output format
- Quality bar (brief, thorough, strict, etc)

## Handoff Rule (Kimi -> Main)
1. Kimi produces draft.
2. Main assistant validates facts, structure, and execution readiness.
3. Main assistant publishes final.

## Failure Recovery
If file is not found:
1. Confirm you are in the same Kimi thread.
2. Re-upload only missing files.
3. Re-run filename listing check.
4. Re-run one transformation check on a known file.

## Quick Test Pack
1. Upload `kimi-link-test.txt`.
2. Ask quote test.
3. Upload `all-md-files.txt`.
4. Ask: "Count files and show first 5 plus last 5."

If all pass, relay is operational.
