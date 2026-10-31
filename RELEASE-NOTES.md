Native Counter-Strike 1.6 packages for all three desktop systems:

- **Windows x64:** extract the Windows ZIP; open `Counter-Strike.exe`.
- **Linux x86_64:** extract the Linux tarball; run `./Play`.
- **macOS 13+, Apple Silicon:** extract the Mac ZIP; open the `.app`.

Default upstream menus, all 67 original Slash maps plus five additional maps
(72 total), all 41 supplied navigation files, native bots, compatible scripts,
LAN host rules and 2× console text. Nine optional host presets include Classic,
DM, FFA, Practice, Knives, Pistols, Surf, Climb and Bhop. New hosted maps start
Classic; remote servers control their own rules.

Existing users can install `Optional-Features.zip` without replacing their
engine or saved preferences. `MODS.md` includes manual instructions and server
bookmarks. Full Zombie/GunGame/Deathrun plugin hosting needs a separate compatible
server stack; universal legacy-server acceptance is not guaranteed.

Mode shortcuts now load through the engine's `userconfig.d` startup folder.
Older upgrades that report unknown mode commands should rerun the installer.
Saved preferences and the installed Mac app are preserved.

Original Half-Life readme and Counter-Strike manual are included in a
`Documentation` folder beside every package, and in the small Documentation.zip.
Open its index.html directly; the native menu's unfinished Readme action remains
unchanged. Existing installations can get the documents with the optional installer.

The repository README includes official engine/client links, public map sources,
manual installation, and builds from Steam data without a private Slash archive.
Public map revisions may differ from this release's snapshot.

Mac headless startup passed on all 72 maps, and native cvar readback passed for
all nine presets and all nine Classic resets. Archive hashes and native binary
architectures were checked on all platforms; the Mac app signature was verified
after extraction. Windows/Linux execution, graphical play and cross-engine
multiplayer need native testing. See `VERIFICATION.json` and `SHA256SUMS.txt`.
