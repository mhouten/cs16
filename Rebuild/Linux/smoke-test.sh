#!/bin/bash
# Test an already statically audited Linux package as an ordinary user.
set -euo pipefail
if [ "$#" -ne 2 ] || [ "$(id -u)" -eq 0 ]; then
    printf '%s\n' "Usage as a non-root user: $0 PACKAGE_DIRECTORY LOG_FILE" >&2
    exit 2
fi
package=$(realpath -- "$1")
log=$(realpath -m -- "$2")
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
ln -s "$package/Play" "$scratch/Counter-Strike Play"
export CS16_NO_DESKTOP=1
export CS16_USERDIR="$scratch/Counter-Strike settings"
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-dummy}"
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-dummy}"
cd "$scratch"
CS16_CHECK_ONLY=1 "./Counter-Strike Play"
wait_for_marker() {
    local marker=$1
    shift
    local runner
    timeout --kill-after=5s 45s "./Counter-Strike Play" "$@" >> "$log" 2>&1 &
    runner=$!
    while kill -0 "$runner" 2>/dev/null; do
        if grep -q "$marker" "$log"; then
            kill -TERM "$runner" 2>/dev/null || true
            wait "$runner" || true
            return 0
        fi
        sleep .2
    done
    printf '%s\n' "Missing startup marker: $marker. See $log." >&2
    return 1
}

# The null renderer can initialize the client and UI without a GPU. Map
# sign-on needs texture loading, so use the dedicated server for the map check.
: > "$log"
wait_for_marker 'Time to first frame:' -dev 2 -ref null -windowed -noip -noip6 \
    +con_fontscale 3 +host_writeconfig
grep -q 'UI_LoadProgs: extended Menu API initialized' "$log"
grep -q 'optional-features.cfg' "$log"
grep -Eq '^con_fontscale[[:space:]]+"?3(\.0+)?"?[[:space:]]*$' "$CS16_USERDIR/cstrike/config.cfg"
wait_for_marker '4 player server started' -dedicated -noip -noip6 +maxplayers 4 +map de_dust2
if grep -Ei 'Host_Error|Crash:|segmentation fault' "$log"; then
    exit 1
fi
printf '%s\n' "Client, menu, dedicated de_dust2 startup and saved console preference passed. Log at $log"
