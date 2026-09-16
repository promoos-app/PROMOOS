#!/usr/bin/env bash
#
# PromoOS — Mongo backup helper.
#
# What it does:
#   1. mongodump the current DB into /app/backups/promoos-YYYY-MM-DD-HHMM.gz
#   2. Prune backups older than $RETENTION_DAYS (default 14)
#   3. Print byte size + collection counts for sanity.
#
# Usage:
#   ./scripts/backup_mongo.sh                       # ad-hoc
#   RETENTION_DAYS=30 ./scripts/backup_mongo.sh     # keep a month
#   OUT_DIR=/mnt/backups ./scripts/backup_mongo.sh  # custom dir
#
# Cron (daily at 03:15 UTC):
#   15 3 * * *  /app/scripts/backup_mongo.sh >> /var/log/promoos-backup.log 2>&1
#
# Restore:
#   mongorestore --uri="$MONGO_URL" --archive=/app/backups/promoos-XXXX.gz --gzip
#
# Requires: mongodump (comes with mongodb-database-tools), env var $MONGO_URL,
# and read access to /app/backend/.env if $MONGO_URL isn't already exported.

set -euo pipefail

if [ -z "${MONGO_URL:-}" ] && [ -f /app/backend/.env ]; then
  # shellcheck disable=SC1091
  export $(grep -E '^(MONGO_URL|DB_NAME)=' /app/backend/.env | xargs -0)
fi

if [ -z "${MONGO_URL:-}" ]; then
  echo "ERROR: MONGO_URL not set. Export it or ensure /app/backend/.env is readable." >&2
  exit 2
fi

if ! command -v mongodump >/dev/null 2>&1; then
  echo "ERROR: mongodump not installed. Install mongodb-database-tools:" >&2
  echo "  apt install mongodb-database-tools   (Debian/Ubuntu)" >&2
  echo "  brew install mongodb/brew/mongodb-database-tools   (macOS)" >&2
  exit 3
fi

OUT_DIR="${OUT_DIR:-/app/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
mkdir -p "$OUT_DIR"

STAMP="$(date -u +%Y-%m-%d-%H%M)"
ARCHIVE="$OUT_DIR/promoos-$STAMP.gz"

echo "▶ Dumping to $ARCHIVE …"
mongodump --uri="$MONGO_URL" --archive="$ARCHIVE" --gzip --quiet

SIZE_BYTES=$(stat -c%s "$ARCHIVE" 2>/dev/null || stat -f%z "$ARCHIVE")
SIZE_HUMAN=$(awk "BEGIN { s=$SIZE_BYTES;
  split(\"B KB MB GB TB\", u); i=1;
  while (s>=1024 && i<5) { s/=1024; i++ }
  printf \"%.2f %s\", s, u[i] }")

echo "✓ Backup complete: $ARCHIVE  ($SIZE_HUMAN)"

# Prune old backups
DELETED=$(find "$OUT_DIR" -type f -name 'promoos-*.gz' -mtime "+$RETENTION_DAYS" -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
  echo "✓ Pruned $DELETED backup(s) older than $RETENTION_DAYS days"
fi

echo "  Retention: $RETENTION_DAYS days · Backup dir: $OUT_DIR"
echo "  Restore:   mongorestore --uri=\"\$MONGO_URL\" --archive=$ARCHIVE --gzip"
