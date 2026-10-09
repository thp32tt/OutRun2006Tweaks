#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cleaner="$repo_root/chrome-cache-clean.sh"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
profile="$tmp/profile"

mkdir -p "$profile/Default/Network" "$profile/Default/Local Storage/leveldb" \
  "$profile/Default/IndexedDB" "$profile/Default/Session Storage" \
  "$profile/Default/Sessions" "$profile/Default/Service Worker/CacheStorage" \
  "$profile/Default/Cache" "$profile/Default/Code Cache" \
  "$profile/Default/GPUCache" "$profile/Default/Network/Cache" \
  "$profile/Code Cache" "$profile/GrShaderCache"
printf 'login-cookie' >"$profile/Default/Network/Cookies"
printf 'auth-idb' >"$profile/Default/IndexedDB/token.db"
printf 'auth-local' >"$profile/Default/Local Storage/leveldb/session"
printf 'session-state' >"$profile/Default/Session Storage/session"
printf 'tabs' >"$profile/Default/Sessions/Current Tabs"
printf 'sw-data' >"$profile/Default/Service Worker/CacheStorage/app-data"
printf 'preference' >"$profile/Default/Preferences"
printf 'password-db' >"$profile/Default/Login Data"
printf 'cache-junk' >"$profile/Default/Cache/entry"
printf 'code-junk' >"$profile/Default/Code Cache/entry"
printf 'gpu-junk' >"$profile/Default/GPUCache/entry"
printf 'network-junk' >"$profile/Default/Network/Cache/entry"
printf 'global-junk' >"$profile/Code Cache/entry"
printf 'shader-junk' >"$profile/GrShaderCache/entry"

CHROME_PROFILE_DIR="$profile" bash "$cleaner" > "$tmp/cleanup-log.txt"
CHROME_PROFILE_DIR="$profile" bash "$cleaner" >> "$tmp/cleanup-log.txt"

for file in \
  "$profile/Default/Network/Cookies" \
  "$profile/Default/IndexedDB/token.db" \
  "$profile/Default/Local Storage/leveldb/session" \
  "$profile/Default/Session Storage/session" \
  "$profile/Default/Sessions/Current Tabs" \
  "$profile/Default/Service Worker/CacheStorage/app-data" \
  "$profile/Default/Preferences" \
  "$profile/Default/Login Data"; do
    test -f "$file"
done
test "$(cat "$profile/Default/Network/Cookies")" = "login-cookie"
test "$(cat "$profile/Default/Local Storage/leveldb/session")" = "auth-local"
for dir in \
  "$profile/Default/Cache" \
  "$profile/Default/Code Cache" \
  "$profile/Default/GPUCache" \
  "$profile/Default/Network/Cache" \
  "$profile/Code Cache" \
  "$profile/GrShaderCache"; do
    test ! -e "$dir"
done

# Do not follow a symlink to an unrelated profile.
mkdir -p "$tmp/elsewhere"
printf 'leave-alone' >"$tmp/elsewhere/Cookies"
ln -s "$tmp/elsewhere" "$tmp/symlink"
CHROME_PROFILE_DIR="$tmp/symlink" bash "$cleaner" >>"$tmp/cleanup-log.txt"
test -f "$tmp/elsewhere/Cookies"
echo "PASS chrome cache cleanup: auth/profile preserved, disposable cache removed twice, symlink refused"
