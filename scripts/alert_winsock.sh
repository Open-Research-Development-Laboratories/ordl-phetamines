#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/development/.secrets/twilio.env"
SEVERITY="${1:-high}"
MESSAGE="${2:-ORDL alert}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ -z "${TWILIO_ACCOUNT_SID:-}" || -z "${TWILIO_AUTH_TOKEN:-}" || -z "${TWILIO_FROM_NUMBER:-}" || -z "${ALERT_TO_NUMBER:-}" ]]; then
  echo "Missing required Twilio env vars" >&2
  exit 1
fi

send_sms() {
  curl -sS -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN" \
    -X POST "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Messages.json" \
    --data-urlencode "To=$ALERT_TO_NUMBER" \
    --data-urlencode "From=$TWILIO_FROM_NUMBER" \
    --data-urlencode "Body=$MESSAGE" >/tmp/ordl_twilio_sms.json
  jq -r '"SMS status: " + (.status // "unknown") + " sid: " + (.sid // "n/a")' /tmp/ordl_twilio_sms.json
}

send_call() {
  local voice_msg
  voice_msg="${MESSAGE//&/and}"
  curl -sS -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN" \
    -X POST "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Calls.json" \
    --data-urlencode "To=$ALERT_TO_NUMBER" \
    --data-urlencode "From=$TWILIO_FROM_NUMBER" \
    --data-urlencode "Twiml=<Response><Say voice='alice'>$voice_msg</Say></Response>" >/tmp/ordl_twilio_call.json
  jq -r '"Call status: " + (.status // "unknown") + " sid: " + (.sid // "n/a")' /tmp/ordl_twilio_call.json
}

case "$SEVERITY" in
  medium)
    send_sms
    ;;
  high|critical)
    send_sms
    send_call
    ;;
  *)
    echo "Unknown severity: $SEVERITY (use medium|high|critical)" >&2
    exit 1
    ;;
esac

echo "Discord fallback channel: #core-council (tandem policy)"
