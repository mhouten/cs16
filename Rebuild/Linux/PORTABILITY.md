# Linux portability

This document describes the source-built Linux package on the portability
branch. The published November 25 archive predates this work. Its
Counter-Strike client requires glibc 2.43.

## Dependency audit

The release builder previously extracted Xash3D FWGS and CS16Client continuous
builds and copied their ELF files without measuring the minimum ABI. The
release lock records the two exact Linux archives. The pinned CS16Client
workflow used `ubuntu-latest` with CMake, while Xash3D's amd64 Linux job used
Ubuntu 22.04 and Waf. Both published more recent glibc symbol requirements. [CS16Client
workflow](https://github.com/FWGS/cs16-client/blob/4120cba6ca205bed0e0b5e02a9ed51e08d73b080/.github/workflows/build.yml)
· [Xash3D workflow](https://github.com/FWGS/xash3d-fwgs/blob/bc1b4515e1f61ebdb76465b498aec1bedde12217/.github/workflows/c-cpp.yml).

Xash3D is
`bc1b4515e1f61ebdb76465b498aec1bedde12217`. The CS16Client continuous tag
resolved to `4120cba6ca205bed0e0b5e02a9ed51e08d73b080`. Gitlinks pin MainUI,
ReGameDLL, YaPB, MiniUTL and the engine's third-party sources. The distribution
previously copied the CS client, MainUI and ReGameDLL. It used ReGameDLL's
native bots. The YaPB module from the client archive was excluded.

GNU `readelf`, `llvm-objdump` and `file` found 19 regular ELF files in the
published Linux archive. They were little-endian x86-64. `xash3d` used
`/lib64/ld-linux-x86-64.so.2`. All other objects were shared libraries.
The maximum required symbol versions are listed below. A dash indicates that
the corresponding import namespace was absent.

| ELF | GLIBC | GLIBCXX | CXXABI | Other versioned providers |
| --- | --- | --- | --- | --- |
| xash3d | 2.34 | – | – | – |
| libxash.so | 2.34 | – | – | GCC_4.2.0 |
| filesystem_stdio.so | 2.33 | 3.4 | 1.3.9 | – |
| libmenu.so | 2.29 | 3.4 | 1.3.9 | GCC_3.3.1 |
| libref_gl.so, libref_gl4es.so, libref_gles1.so, libref_gles2.so, libref_gles3compat.so | 2.29 | – | – | – |
| libref_null.so | – | – | – | – |
| libSDL2-2.0.so.0.3200.10 | 2.34 | – | – | – |
| libavcodec.so.63.1.102 | 2.27 | – | – | LIBAVUTIL_61, LIBSWRESAMPLE_7 |
| libavformat.so.63.1.102 | 2.14 | – | – | LIBAVCODEC_63, LIBAVUTIL_61 |
| libavutil.so.61.1.102 | 2.28 | – | – | – |
| libswresample.so.7.1.102 | 2.14 | – | – | LIBAVUTIL_61 |
| libswscale.so.10.1.102 | 2.27 | – | – | LIBAVUTIL_61 |
| cstrike/cl_dlls/client_amd64.so | **2.43** | 3.4 | 1.3.9 | GCC_3.0 |
| cstrike/cl_dlls/menu_amd64.so | 2.38 | 3.4 | 1.3.8 | GCC_3.0 |
| cstrike/dlls/cs_amd64.so | **2.43** | 3.4.15 | 1.3 | – |

The exact 2.43 imports are `acosf` and `atan2f` in the client, and `acosf`,
`atan2f` and `sqrtf` in ReGameDLL, all exported by `libm.so.6`. The loader
rejected the old client on both AlmaLinux 8 and Debian 11 after static
inspection. Its diagnostic also reported 2.34 and 2.38 requirements. The
engine and SDL independently exceed 2.28, so replacing the client alone would
leave additional failures.

The old package's engine launcher and engine library used a `$ORIGIN`
RUNPATH. ReGameDLL used `$ORIGIN/.`. The rest depended on the default loader
paths or the launcher's `LD_LIBRARY_PATH`. FFmpeg providers were present
locally but required the broadcast search path for transitive resolution. The
CS menu required host `libfreetype.so.6`, which a minimal install could lack.
Graphics, sound and input drivers loaded through SDL are outside DT_NEEDED.
Static inspection therefore cannot establish desktop compatibility.

## Approaches evaluated

| Approach | Compatibility, overhead and maintenance |
| --- | --- |
| Older glibc baseline | One build for hosts at or above its ABI floor. Native process, graphics and network performance. Requires a maintained compiler and a symbol gate. |
| Pinned OCI build | Isolates the compiler, headers and sysroot, and allows an offline compile after fetching. Build-time cost only. Image and toolchain updates are visible in release provenance. |
| Private redistributable libraries | Ships SDL and the FFmpeg libraries used by the engine, tracks their licenses and update inputs, and keeps the host's graphics/audio stack in charge. Adds a few megabytes. |
| `$ORIGIN` RUNPATH | Resolves each object's own private dependencies after relocation. Limits the search to package directories without a machine-wide library path. No runtime packaging layer. |
| Selective static linking | Links FreeType into MainUI and uses the engine's upstream bundled codec configuration. Removes separate library discovery and adds only used code. Updates require a rebuild. Keep glibc dynamic for host integration. |
| AppImage | A convenient wrapper carries the same ABI floor and adds mount or extract integration and compatibility testing. It would still need this rebuild and host driver access. |
| Steam Linux Runtime | Useful when integrating with Steam. Its userspace container adds download, storage and a host-driver bridge. Steam-only integration adds a second support path for an otherwise standalone game. |
| Multiple glibc builds | Useful if a dependency genuinely requires a different ABI. Duplicates archive storage, release/desktop testing and support. |
| musl build | A separate port needs source and SDL/driver testing on musl. Compatibility layers have different coverage and are outside this release. |

References: [Xash3D build guide](https://github.com/FWGS/xash3d-fwgs/blob/bc1b4515e1f61ebdb76465b498aec1bedde12217/README.md),
[CS16Client build guide](https://github.com/FWGS/cs16-client/blob/4120cba6ca205bed0e0b5e02a9ed51e08d73b080/README.md),
[AppImage requirements](https://docs.appimage.org/reference/best-practices.html),
[Steam Runtime design](https://github.com/ValveSoftware/steam-runtime/blob/master/doc/goals.md).

## Build architecture and release gates

1. Verify pinned source archives and check out exact engine and client
   revisions and Gitlinks. Build in a digest-pinned AlmaLinux 8 x86-64 image
   with GCC Toolset 14 and the glibc 2.28 sysroot. The base image is pinned;
   signed AlmaLinux RPM and Ubuntu SDK package versions are recorded in the
   output. SDL uses selected Ubuntu 22.04 headers to preserve its dynamically
   loaded desktop backends. The compiler runs offline after input acquisition.
2. Build the engine, filesystem, main menu, renderers, SDL, CS16Client,
   MainUI and ReGameDLL. Explicitly link the client and MainUI to `libdl`
   for older glibc. Resolve ReGameDLL's filesystem module through its private
   RUNPATH so bots can start when Xash3D enters a separate writable profile.
   The Linux package's `cstrike.rc` schedules the engine's `+` arguments.
   Use the locked LGPL FFmpeg build only after the ELF
   gate passes. Keep the original, checksum-verified PK3 resources and game
   data. Stage the private native libraries with relative RUNPATH entries.
3. Reject any package object over the ABI cap or with an unexpected
   architecture, interpreter, dependency or search path. Check private
   providers and their symbol versions. Use `ldd -v` on a trusted runtime after
   static checks succeed. Package only after the assembled tree passes.
4. Generate SHA-256 and audit the packed archive again before publication.
   GitHub Actions validates the runtime only when manually dispatched.
   Full asset packaging runs locally with authorized game data.

Target ABI is **x86-64, SSE3, glibc 2.28**, with GCC 8-era host ABI limits
`GLIBCXX_3.4.25`, `CXXABI_1.3.11` and `GCC_7.0.0`.
A 2.31 floor would cover Ubuntu 20.04 and Debian 11 but miss Enterprise Linux 8.
A 2.35 floor would also miss Ubuntu 20.04 and Debian 11. Either higher floor
would still need a rebuild of the current client, menu and ReGameDLL. The
2.28 base image runs and supplies the required host ABI family. See the test
status below for the resulting package.

ReGameDLL's upstream build enables SSE3. The launcher reports an outdated CPU
when Linux exposes its x86 feature flags.

The runtime keeps glibc, `libgcc_s`, `libstdc++`, the dynamic loader and
the display/audio driver stack on the host. OpenGL or GLES, X11 or Wayland
and the session's audio libraries are discovered by SDL at runtime. Supply
the corresponding host driver and session where needed. A standard desktop
normally provides them. SDL supports ALSA, PulseAudio, PipeWire, JACK, NAS
and sndio where the corresponding host service and library are available.
Wayland can use the host's libdecor for client-side window decorations. Networking remains in the native engine, so
this approach adds no proxy or container network to player sessions.

The inputs and notices are inventoried in [sources.json](sources.json).
See the [FFmpeg source and build definitions](https://github.com/FWGS/FFmpeg-Builds)
and the [FreeType license](../Licenses/FreeType-FTL.txt). This work uses
existing game assets and maintains their provenance. A source build requires
your own Steam or supplied game files and separately obtained map resources.

## Player and builder checks

Run the correct archive's `./Play` from any working directory. The install
directory must allow execution. Settings normally save inside `Game/`.
For a read-only install, run
`CS16_USERDIR="$HOME/.local/share/cs16-profile" ./Play` to use a writable profile.
The original command line arguments pass to the engine.

- Run `CS16_CHECK_ONLY=1 ./Play` to diagnose required ELF libraries.
- If the loader reports `GLIBC_2.43`, verify that the archive is the
  source-built Linux release and that it was fully extracted into a fresh
  directory. Mixing old and new modules can reproduce the error.
- For video troubleshooting, try `SDL_VIDEODRIVER=x11 ./Play` with XWayland or
  `SDL_VIDEODRIVER=wayland ./Play` in a Wayland session.
- For audio troubleshooting, try `SDL_AUDIODRIVER=pulseaudio ./Play` with a
  PulseAudio-compatible session or `SDL_AUDIODRIVER=alsa ./Play` with ALSA.

Audit a staged directory or a tar.gz with Python 3.12+ and GNU binutils.

```sh
python3 Rebuild/Scripts/audit-linux.py /path/to/Counter-Strike-1.6-linux.tar.gz \
  --report /path/to/linux-elf.txt
```

Set a consistent `SOURCE_DATE_EPOCH` when comparing Linux archives built
from identical inputs. The packager normalizes tar ownership and timestamps
and records SHA-256. Retain the builder image and recorded package manifests
for repeat builds with the same toolchain.

Run `--host` only for trusted artifacts and only on glibc Linux. Run
`Rebuild/Linux/smoke-test.sh PACKAGE_DIRECTORY LOG_FILE` as an ordinary user
to exercise the relocated launcher, real client, local map and settings.
The null renderer and dummy audio cover startup independently of the desktop.

## Validation results

The staged Linux tar.gz passed static validation for all **19 ELF objects**.
The AlmaLinux 8 loader resolved every required library after the static gate.
The largest imports in the archive were `GLIBC_2.28`, `GLIBCXX_3.4.15`,
`CXXABI_1.3.9` and `GCC_4.2.0`. Validation also matched all 4,960 shared
content hashes, both original resource PK3s, 72 maps and 41 navigation files.

| Distribution | Scope verified |
| --- | --- |
| AlmaLinux 8, glibc 2.28 | Relocated client and menu startup, saved settings, all 72 dedicated map startups, a native bot join, and all nine modes and their Classic resets. |
| Debian 11 and Ubuntu 20.04, glibc 2.31 | Relocated client and menu startup, dedicated `de_dust2` startup and saved settings. |
| Fedora 44, glibc 2.43 | Same startup and storage checks. Virtual X11 and Wayland reached local-game sign-on with software OpenGL in windowed and fullscreen modes. An X11 audio probe captured nonzero PulseAudio PCM from a bundled sound. |
| Arch, glibc 2.44 | Relocated client and menu startup, dedicated `de_dust2` startup and saved settings. |
| Rocky Linux 8+, newer AlmaLinux and Debian, MX Linux based on Debian 11+, newer Ubuntu, Ubuntu-based Mint, Pop!_OS and Zorin OS | ABI targets. Distribution-specific desktop testing pending. |
| Manjaro, EndeavourOS, other Fedora releases, openSUSE Leap and Tumbleweed | ABI targets where the installed runtime meets the floor. Distribution-specific desktop testing pending. |
| SteamOS 3 | ABI target in desktop mode. Steam, Gamescope and controller testing pending. |
| Alpine 3.23 and other musl distributions | Alpine produced the expected launcher message. These systems need a separate native build. |
| ARM64 or 32-bit x86 Linux | Separate package required. |

All runnable environments used amd64 containers on Docker Desktop. The
launcher tests used a non-root user, a symlink and an unrelated working
directory. The installation was mounted read-only at a path containing
spaces and settings were saved in an isolated writable profile.

A Fedora virtual X11 client completed native multiplayer sign-on to a second
container running the AlmaLinux 8 dedicated server on an isolated IPv4 LAN.
Direct connection was exercised. LAN discovery, a physical multi-device LAN,
public servers and Steam/legacy GoldSrc authentication remain unverified.

The OpenGL tests exercised the real menu and map initialization in virtual
displays. Physical GPU acceleration, visual fidelity, hardware audio,
keyboards, mice and controllers remain unverified. The map checks retain
the original 37 navigation version warnings.
