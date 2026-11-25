#!/bin/bash
# Run via build-linux-runtime.py, with verified inputs and networking disabled.
set -euo pipefail
export LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=1795480907
jobs=$1
test "$(uname -m)" = x86_64
test "$(getconf GNU_LIBC_VERSION)" = "glibc 2.28"
root=$(mktemp -d)
cd "$root"
for name in sdl freetype patchelf ffmpeg; do
    mkdir "$name"
    case "$name" in
        ffmpeg) ext=xz ;;
        *) ext=gz ;;
    esac
    tar -xf "/inputs/$name.tar.$ext" -C "$name" --strip-components=1
done
cp -a /inputs/upstream-engine engine
cp -a /inputs/upstream-client client

export CFLAGS="-O2 -march=x86-64 -mtune=generic -ffile-prefix-map=$root=/usr/src/cs16"
export CXXFLAGS="$CFLAGS" CC=gcc CXX=g++
bash /recipe/build-sdl.sh "$jobs"
# FreeType is linked into the CS menu. The engine menu follows its upstream
# configuration and uses stb_truetype.
cmake -S freetype -B freetype-build -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$root/freetype-install" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_SHARED_LIBS=OFF \
    -DFT_DISABLE_ZLIB=ON -DFT_DISABLE_BZIP2=ON -DFT_DISABLE_PNG=ON \
    -DFT_DISABLE_HARFBUZZ=ON -DFT_DISABLE_BROTLI=ON
cmake --build freetype-build --parallel "$jobs"
cmake --install freetype-build
(cd patchelf && ./configure --prefix="$root/patchelf-install" && make -j"$jobs" && make install)

# The build uses the release's existing audited resources. Upstream CMake
# normally downloads new YaPB graphs while configuring even for offline builds.
sed -i '/^execute_process($/,/^)/ { /yapb_graph_dl.py/ s|.*|\t-c "pass"|; }' client/CMakeLists.txt
# glibc 2.28 exposes dlopen/dlsym in libdl. Newer build hosts can
# inadvertently mask the missing link declarations in these two targets.
cat >> client/cl_dll/CMakeLists.txt <<'CMAKE'

target_link_libraries(client ${CMAKE_DL_LIBS})
CMAKE
cat >> client/3rdparty/mainui_cpp/CMakeLists.txt <<'CMAKE'

target_link_libraries(menu ${CMAKE_DL_LIBS})
CMAKE
git -C client/3rdparty/ReGameDLL_CS apply --ignore-space-change /recipe/regamedll-filesystem.patch
cmake -S client -B client-build -DCMAKE_BUILD_TYPE=Release -DPython_EXECUTABLE=/usr/bin/python3.12 \
    -DCMAKE_PREFIX_PATH="$root/freetype-install"
# The upstream archive also builds YaPB. This distribution uses the
# ReGameDLL bots, as in the original Linux package.
cmake --build client-build --parallel "$jobs" --target client menu regamedll

(
    cd engine
    python3.12 waf configure -8 --disable-werror --enable-bundled-deps --enable-stbtt \
        --enable-all-renderers --enable-ffmpeg --enable-ffmpeg-dlopen \
        --ffmpeg-dir="$root/ffmpeg" -s "$root/sdl-install"
    python3.12 waf build -j"$jobs"
    python3.12 waf install --destdir="$root/engine-install"
)

package=$root/package
game=$package/Game
mkdir -p "$game/cstrike/cl_dlls" "$game/cstrike/dlls" "$game/Linux-Licenses"
install -m 755 /recipe/Play "$package/Play"
cp "$root/engine-install"/xash3d "$root/engine-install"/*.so "$game/"
cp -a "$root/sdl-install"/lib/libSDL2-2.0.so.* "$root/ffmpeg"/lib/lib{av,sw}*.so.* "$game/"
cp client-build/cl_dll/client_amd64.so client-build/3rdparty/mainui_cpp/menu_amd64.so "$game/cstrike/cl_dlls/"
cp client-build/3rdparty/ReGameDLL_CS/regamedll/cs_amd64.so "$game/cstrike/dlls/"
find "$game" -type f -print0 | while IFS= read -r -d '' binary; do
    rpath="\$ORIGIN"
    if [ "$binary" = "$game/cstrike/dlls/cs_amd64.so" ]; then
        rpath="\$ORIGIN/../.."
    fi
    "$root/patchelf-install/bin/patchelf" --set-rpath "$rpath" "$binary"
    strip --strip-debug "$binary"
done
cp sdl/LICENSE.txt "$game/Linux-Licenses/SDL.txt"
cp freetype/docs/FTL.TXT "$game/Linux-Licenses/FreeType.txt"
cp client/LICENSE "$game/Linux-Licenses/CS16Client.txt"
cp client/3rdparty/ReGameDLL_CS/LICENSE "$game/Linux-Licenses/ReGameDLL.txt"
find ffmpeg -maxdepth 2 -type f \( -iname '*license*' -o -iname '*copying*' \) \
    -exec cp -t "$game/Linux-Licenses" {} +
cp /recipe/sources.json /recipe/regamedll-filesystem.patch "$game/Linux-Licenses/"
{
    getconf GNU_LIBC_VERSION
    gcc --version | head -1
    cmake --version | head -1
    rpm -qa | sort
    cat /opt/sdl-sdk/packages.txt
    for source in engine client; do
        git -C "$source" rev-parse HEAD
        git -C "$source" submodule status --recursive
    done
} > "$game/Linux-Licenses/build-environment.txt"
python3.12 /scripts/audit-linux.py "$package" --host --report /output/ELF-REPORT.txt
cp -a "$game" "$package/Play" /output/
