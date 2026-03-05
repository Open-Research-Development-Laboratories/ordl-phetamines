# DISCORD.md

Discord specific rules from Winsock. These are mandatory.

## DM Protocol

1. Triage first, no immediate reply by default.
2. Send Winsock a one line intake: sender and short intent summary.
3. Wait for action code:
   - A allow one reply
   - B open shared thread or channel with Winsock
   - C ignore
   - D blocklist sender
   - E draft reply for Winsock approval
4. Auto rules:
   - trusted allowlist can receive immediate replies
   - unknown users require approval
   - repeat spam gets silent deny
5. Optional digest mode for non urgent DMs (30m or 60m batches). Urgent keywords bypass digest.
6. If Winsock says pause or no messages in Discord, do not send messages until explicit resume phrase: "Winsock authorizes full discord usage again."
7. Before any Discord send, verify pause status in current chat context.
8. Keep a visible outbound log at `logs/DISCORD-OUTBOUND.md` with timestamp, target, and exact sent text.
9. If a rule is violated, report it to Winsock immediately in this chat with exact message content.
10. Group channels default to silent mode. Reply only when directly asked, directly mentioned with a clear request, or explicitly delegated by Winsock.
11. If Winsock says "quiet", "stop", "don't reply", or equivalent, respond with NO_REPLY until Winsock gives an explicit resume instruction.
12. Do not interpret casual chatter, celebrations, or status updates as a request for a reply.
