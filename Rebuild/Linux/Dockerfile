# Build-only headers and SONAME discovery files for SDL's dynamic backends.
# The game is linked and audited on the separate AlmaLinux 8 stage below.
FROM public.ecr.aws/ubuntu/ubuntu@sha256:b682e31336cc8e0a73ed91ab32b7a95e32591c5ff09994490a20accf9b3600f9 AS sdl-sdk
RUN apt-get update && apt-get install -y --no-install-recommends \
      libaudio-dev libdecor-0-dev libjack-jackd2-dev libpipewire-0.3-dev libsamplerate0-dev libsndio-dev \
    && mkdir -p /opt/sdl-sdk/include /opt/sdl-sdk/lib/pkgconfig \
    && cd /usr/include \
    && cp -a audio libdecor-0 jack pipewire-0.3 spa-0.2 samplerate.h sndio.h /opt/sdl-sdk/include/ \
    && cd /usr/lib/x86_64-linux-gnu \
    && cp -a libaudio.so* libdecor-0.so* libjack.so* libpipewire-0.3.so* libsamplerate.so* libsndio.so* /opt/sdl-sdk/lib/ \
    && cd pkgconfig \
    && cp -a jack.pc libdecor-0.pc libpipewire-0.3.pc libspa-0.2.pc samplerate.pc sndio.pc /opt/sdl-sdk/lib/pkgconfig/ \
    && sed -i 's|^prefix=/usr$|prefix=/opt/sdl-sdk|; s|^libdir=.*$|libdir=/opt/sdl-sdk/lib|' /opt/sdl-sdk/lib/pkgconfig/*.pc \
    && dpkg-query -W > /opt/sdl-sdk/packages.txt

# AlmaLinux 8 x86_64. The compiler and desktop development libraries stay in the builder.
FROM quay.io/almalinuxorg/almalinux@sha256:18fb4641b9cb006781070b26180ea00e9d33c30ed0de7a1e3d6a30bc1eb09a2f
RUN --mount=type=cache,target=/var/cache/dnf,sharing=locked \
    dnf -y --setopt=keepcache=1 --setopt=install_weak_deps=False --enablerepo=powertools install \
      gcc-toolset-14-gcc-c++ cmake make git python3.12 binutils file pkgconf-pkg-config \
      alsa-lib-devel pulseaudio-libs-devel libX11-devel libXext-devel libXrandr-devel \
      libXcursor-devel libXfixes-devel libXi-devel libXScrnSaver-devel wayland-devel \
      libxkbcommon-devel mesa-libGL-devel mesa-libEGL-devel mesa-libGLES-devel \
      mesa-libgbm-devel libdrm-devel dbus-devel systemd-devel
ENV PATH="/opt/rh/gcc-toolset-14/root/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
COPY --from=sdl-sdk /opt/sdl-sdk /opt/sdl-sdk
