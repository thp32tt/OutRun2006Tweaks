#!/usr/bin/env bash
set -euo pipefail

# Safe only with Chrome stopped. Preserve all authentication and page data:
# Network/Cookies, Cookies, Login Data, Preferences, Local Storage, IndexedDB,
# Session Storage, Sessions, Service Worker and extensions are NEVER removed.
# These named directories contain disposable browser cache, not credentials.
profile="${CHROME_PROFILE_DIR:-/data/browser-profile}"
if [[ ! -d "$profile" || -L "$profile" ]]; then
  echo "cache-clean: profile missing or symlink; nothing removed"
  exit 0
fi
if [[ -L "$profile/Default" ]]; then
  echo "cache-clean: Default profile symlink refused"
  exit 0
fi

cache_dirs=(
  "Cache"
  "Code Cache"
  "GPUCache"
  "GrShaderCache"
  "ShaderCache"
  "DawnCache"
  "Default/Cache"
  "Default/Code Cache"
  "Default/GPUCache"
  "Default/GrShaderCache"
  "Default/ShaderCache"
  "Default/DawnCache"
  "Default/Media Cache"
  "Default/Network/Cache"
)
cleaned=0
for relative in "${cache_dirs[@]}"; do
  candidate="$profile/$relative"
  if [[ -d "$candidate" && ! -L "$candidate" ]]; then
    rm -rf -- "$candidate"
    cleaned=$((cleaned + 1))
  fi
done
echo "cache-clean: removed $cleaned disposable cache directories; credentials and storage preserved"
