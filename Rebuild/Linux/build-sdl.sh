#!/bin/bash
# Keep SDL's desktop integrations dynamically loaded from the player's host.
set -euo pipefail
jobs=$1
root=$PWD
sdk=/opt/sdl-sdk
PKG_CONFIG_PATH="$sdk/lib/pkgconfig" cmake -S sdl -B sdl-build \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$root/sdl-install" \
    -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_LIBRARY_PATH="$sdk/lib" \
    -DCMAKE_C_FLAGS="$CFLAGS -I$sdk/include" \
    -DSDL_STATIC=OFF -DSDL_RENDER=OFF -DSDL_TEST=OFF \
    -DSDL_X11=ON -DSDL_WAYLAND=ON
config=sdl-build/SDL_config.h.intermediate
for driver in SDL_VIDEO_DRIVER_X11 SDL_VIDEO_DRIVER_WAYLAND SDL_AUDIO_DRIVER_ALSA \
    SDL_AUDIO_DRIVER_PULSEAUDIO SDL_AUDIO_DRIVER_PIPEWIRE SDL_AUDIO_DRIVER_JACK \
    SDL_AUDIO_DRIVER_NAS SDL_AUDIO_DRIVER_SNDIO HAVE_LIBSAMPLERATE_H HAVE_LIBDECOR_H; do
    grep -q "^#define $driver 1$" "$config" ||
        { printf '%s\n' "Required SDL feature missing: $driver" >&2; exit 1; }
done
cmake --build sdl-build --parallel "$jobs"
cmake --install sdl-build
