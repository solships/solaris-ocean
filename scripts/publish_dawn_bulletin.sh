#!/bin/zsh
# Daily dawn-bulletin publisher.
# 1) Generate today's bulletin from the latest ocean fetch.
# 2) Build the Astro site.
# 3) Deploy to Vercel prod.
# 4) Alias the new deployment to currentsolaris.vercel.app.
# Logs everything to ~/.solaris/dawn_publish.log.

set -eo pipefail

PROJECT="/Users/kayla/solaris-ocean"
LOG="$HOME/.solaris/dawn_publish.log"
mkdir -p "$(dirname "$LOG")"

echo "" >> "$LOG"
echo "=== Dawn publish $(date -Iseconds) ===" >> "$LOG"

cd "$PROJECT"

# Ensure PATH includes homebrew-installed binaries (vercel, node, npm).
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "[1a/4] Fetching fresh ocean reading (lite)..." >> "$LOG"
TMP_READINGS="/tmp/solaris_dawn_readings.json"
/usr/bin/python3 "$PROJECT/scripts/fetch_ocean_lite.py" "$TMP_READINGS" >> "$LOG" 2>&1

echo "[1b/4] Generating bulletin..." >> "$LOG"
SOLARIS_READINGS="$TMP_READINGS" /usr/bin/python3 "$PROJECT/scripts/dawn_bulletin.py" >> "$LOG" 2>&1

echo "[2/4] Building site..." >> "$LOG"
/opt/homebrew/bin/npm run build >> "$LOG" 2>&1

echo "[3/4] Deploying to Vercel..." >> "$LOG"
DEPLOY_URL=$(/opt/homebrew/bin/vercel --prod --yes 2>>"$LOG" | tee -a "$LOG" | grep -oE "https://currentsolaris-[a-z0-9]+-solarlovesong[^ ]+\.vercel\.app" | head -1)

if [[ -z "$DEPLOY_URL" ]]; then
  echo "ERROR: could not parse deploy URL" >> "$LOG"
  exit 1
fi

echo "[4/4] Aliasing to currentsolaris.vercel.app..." >> "$LOG"
/opt/homebrew/bin/vercel alias set "$DEPLOY_URL" currentsolaris.vercel.app >> "$LOG" 2>&1

echo "Done: $DEPLOY_URL" >> "$LOG"
