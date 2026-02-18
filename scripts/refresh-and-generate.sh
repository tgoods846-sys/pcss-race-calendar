#!/usr/bin/env bash
set -euo pipefail

# Refresh race database and generate social images
# Usage: bash scripts/refresh-and-generate.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== Refreshing race database ==="
python3 -m ingestion.refresh

echo "=== Copying database to site ==="
cp data/race_database.json site/data/race_database.json

echo "=== Generating weekly preview images ==="
python3 -m social.generate --type weekly_preview

echo "=== Generating weekend preview images ==="
python3 -m social.generate --type weekend_preview

CURRENT_MONTH=$(python3 -c "from datetime import date; print(date.today().strftime('%Y-%m'))")
echo "=== Generating monthly calendar ($CURRENT_MONTH) ==="
python3 -m social.generate --type monthly_calendar --month "$CURRENT_MONTH"

NEXT_MONTH=$(python3 -c "
from datetime import date, timedelta
today = date.today()
first_next = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
print(first_next.strftime('%Y-%m'))
")
echo "=== Generating monthly calendar ($NEXT_MONTH) ==="
python3 -m social.generate --type monthly_calendar --month "$NEXT_MONTH"

echo "=== Done! Output in output/social/ ==="
