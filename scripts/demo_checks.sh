#!/usr/bin/env bash
# Demo API checks for judges / smoke testing (requires API on localhost:8000)
set -euo pipefail
API="${API_URL:-http://localhost:8000/api/v1}"

echo "=== Health ==="
curl -s "$API/../health" | head -c 200
echo ""

echo "=== Scam check (SBP loan) ==="
SCAM=$(curl -s -X POST "$API/scamcheck/submit" \
  -H "Content-Type: application/json" \
  -d '{"text":"SBP approved your loan. Send OTP to release funds immediately."}')
echo "$SCAM"
CHECK_ID=$(echo "$SCAM" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('id') or d.get('check_id',''))")

if [ -n "$CHECK_ID" ]; then
  echo "Polling check $CHECK_ID ..."
  for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 3
    RES=$(curl -s "$API/checks/$CHECK_ID")
    STATUS=$(echo "$RES" | python -c "import sys,json; print(json.load(sys.stdin).get('status',''))")
    echo "  attempt $i: status=$STATUS"
    if [ "$STATUS" = "complete" ] || [ "$STATUS" = "error" ]; then
      echo "$RES" | python -m json.tool | head -40
      break
    fi
  done
fi

echo "=== Fact check ==="
curl -s -X POST "$API/factcheck/submit" \
  -H "Content-Type: application/json" \
  -d '{"text":"Pakistan inflation rate is 50 percent this year"}' | head -c 300
echo ""
