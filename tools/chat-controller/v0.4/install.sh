#!/usr/bin/env bash
set -euo pipefail

DEST="${DEST:-/opt/outrun-chat-controller}"
BASE="https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/chat-controller-downloads/tools/chat-controller/v0.4"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

command -v curl >/dev/null || { echo "curl required"; exit 1; }
command -v base64 >/dev/null || { echo "base64 required"; exit 1; }
command -v sha256sum >/dev/null || { echo "sha256sum required"; exit 1; }

if ! command -v unzip >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y unzip
fi

: > "$TMP/controller.b64"
for n in 00 01 02 03 04 05 06 07 08 09 10 11; do
  curl -fsSL "$BASE/part${n}.b64" >> "$TMP/controller.b64"
done

tr -d '\r\n\t ' < "$TMP/controller.b64" | base64 -d > "$TMP/controller.zip"
echo "119aa620bbf6ae4dc26cdc48e2ed48f645ad281cae4645bbe96fe25c37f192e9  $TMP/controller.zip" | sha256sum -c -

mkdir -p "$TMP/unpack"
unzip -oq "$TMP/controller.zip" -d "$TMP/unpack"

sudo mkdir -p "$DEST"
sudo chown -R "$USER":"$USER" "$DEST"
cp -a "$TMP/unpack/outrun-chat-controller/." "$DEST/"

echo "Installed: $DEST"
echo "Next:"
echo "  cd $DEST"
echo "  nano docker-compose.yml"
echo "  docker compose up -d --build"
