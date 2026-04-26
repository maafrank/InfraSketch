#!/bin/bash
# Hit one endpoint per split routes_*.py file in production to confirm the
# Phase 2 split + Depends conversion didn't break auth or routing.
#
# Usage:
#   1. Sign into https://infrasketch.net in your browser.
#   2. Open DevTools console and run:
#        await window.Clerk.session.getToken()
#      Copy the token (it starts with "eyJ...").
#   3. Run this script:
#        CLERK_TOKEN='eyJ...' bash scripts/smoke_prod_endpoints.sh
#
# The script creates a throwaway session, exercises the session-scoped
# endpoints, then deletes it. You should see all OKs. Any FAIL means
# auth, routing, or a Depends dependency broke after the cleanup.

set -u
API="${API:-https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod}"

if [ -z "${CLERK_TOKEN:-}" ]; then
    echo "Set CLERK_TOKEN env var first (see usage at top of script)."
    exit 1
fi

PASS=0
FAIL=0
H="Authorization: Bearer $CLERK_TOKEN"

probe() {
    local label="$1"; local expected="$2"; shift 2
    local code
    code=$(curl -sS -o /tmp/smoke-body -w "%{http_code}" "$@") || code="curl-err"
    if [ "$code" = "$expected" ]; then
        printf "  OK    %-58s (%s)\n" "$label" "$code"
        PASS=$((PASS+1))
    else
        printf "  FAIL  %-58s (got %s, expected %s)\n" "$label" "$code" "$expected"
        echo "        body: $(head -c 200 /tmp/smoke-body)"
        FAIL=$((FAIL+1))
    fi
}

echo "Smoke against $API"
echo
echo "--- public (no auth) ---"
probe "GET    /badges/monthly-visitors.svg     [routes.py]"           200 \
  "$API/api/badges/monthly-visitors.svg"

echo
echo "--- auth-only ---"
probe "GET    /user/preferences                [routes_users.py]"     200 -H "$H" \
  "$API/api/user/preferences"
probe "GET    /user/sessions                   [routes_users.py]"     200 -H "$H" \
  "$API/api/user/sessions"
probe "GET    /user/gamification               [routes_users.py]"     200 -H "$H" \
  "$API/api/user/gamification"
probe "GET    /user/credits                    [routes_billing.py]"   200 -H "$H" \
  "$API/api/user/credits"
probe "GET    /user/credits/history            [routes_billing.py]"   200 -H "$H" \
  "$API/api/user/credits/history"
probe "GET    /subscription/status             [routes_billing.py]"   200 -H "$H" \
  "$API/api/subscription/status"

echo
echo "--- create session, exercise, then delete ---"
SID=$(curl -sS -X POST -H "$H" "$API/api/session/create-blank" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["session_id"])' 2>/dev/null) \
      || SID=""
if [ -z "$SID" ]; then
    echo "  FAIL  POST /session/create-blank   could not parse session_id"
    FAIL=$((FAIL+1))
else
    printf "  OK    %-58s (sid=%s)\n" "POST   /session/create-blank             [routes.py]" "$SID"
    PASS=$((PASS+1))

    probe "GET    /session/{id}                    [routes.py]"             200 -H "$H" \
      "$API/api/session/$SID"
    probe "POST   /session/{id}/nodes              [routes_diagrams.py]"    200 -H "$H" \
      -H 'Content-Type: application/json' \
      -d '{"id":"smoke-node-1","type":"server","label":"smoke","description":"","inputs":[],"outputs":[],"metadata":{"technology":"","notes":""},"position":{"x":0,"y":0}}' \
      -X POST "$API/api/session/$SID/nodes"
    probe "GET    /session/{id}/diagram/status     [routes_diagrams.py]"    200 -H "$H" \
      "$API/api/session/$SID/diagram/status"
    probe "GET    /session/{id}/design-doc/status  [routes_design_docs.py]" 200 -H "$H" \
      "$API/api/session/$SID/design-doc/status"

    # Cleanup
    probe "DELETE /session/{id}                    [routes.py]"             200 -H "$H" \
      -X DELETE "$API/api/session/$SID"
fi

echo
echo "--- negative: missing token must 401 (verifies ClerkAuthMiddleware) ---"
probe "GET    /user/credits  (no auth)" 401 "$API/api/user/credits"

echo
echo "=== $PASS passed, $FAIL failed ==="
exit $FAIL
