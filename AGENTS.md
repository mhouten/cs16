# Counter-Strike 1.6 distribution project

Treat this directory as the project root. Read `AGENT_CONTEXT.md` and `README.md`
before making changes. All paths in these instructions are relative to here;
the original parent workspace is not required to use the packages or rebuild kit.

## User requirements

- Keep complete macOS Apple Silicon, Linux x86_64, and Windows x64 packages here.
- Use default upstream CS16Client/MainUI menus. Do not restore Slash menu art,
  colors, startup music, or forced graphics settings.
- Keep all 67 Slash CS maps, 41 navigation files, compatible scripts/rules,
  native bots, and the supplied silver/soldier icon.
- Keep console text readable: the current new-install default is
  `con_fontscale "2"`. Save this in `config.cfg`, not an autoexec that overrides
  the player's own saved preference on every run.
- Maintain direct official component links and full manual rebuild instructions.
  The user has no original Slash download URL; never invent one.
- Keep project context and agent instructions inside this directory.
- Include optional host modes, currently Classic, DM, FFA, Practice, Knives,
  Pistols, Surf, Climb and Bhop. Do not activate them from client startup.
  New hosted maps reset to Classic. Preserve normal server joining and do not
  claim universal GoldSrc authentication or native AMXX plugin compatibility.
- Retain the original 67 maps and 41 navs; five extra public maps bring the total
  to 72. Keep the manual add-on installer separate from engine/client libraries.
- Repository: `git@github.com:mhouten/cs16.git`. Publish all three OS archives
  as GitHub Release assets; keep large packages out of Git history. The public
  README should be concise, with original download links and rebuild steps.
- Support Steam data plus public map downloads through `--source`; retain the
  original `--slash` alias. Do not require a private Slash archive for that path.
  Exact old asset revisions still need matching source content.

## Working files

- `Rebuild/Scripts/package-slash.py` is the active builder. `--menu default` is
  the default. Other scripts beside it are required helpers.
- `Rebuild/Scripts/verify-slash.py` verifies assembled package directories and
  can run native Mac headless map checks. See its `--help`.
- `Rebuild/Icons/Source.png` is the user's original icon. Preserve it; use
  `Rebuild/Scripts/make-app-icons.py` for platform icon containers.
- `Rebuild/content-manifest.json` records exact shared content hashes;
  `Rebuild/upstream-lock.json` pins the release archives used in this build.
- `VERIFICATION.json` records results and limits; `SHA256SUMS.txt` covers the
  published deliverables. `README.md` is the main player/rebuild guide.
- `MAPS.md` and `Rebuild/map-sources.json` record public map downloads and
  comparison status. `Rebuild/Defaults/cstrike/` supplies the portable preset.
  The exact `breakfloor_b5` fallback is in `Rebuild/Maps/` because its mirror is offline.
- `Rebuild/Scripts/publish-release.py` verifies checksums and publishes all three
  prepared packages with `gh`; authenticate first. Upload large archives only
  to Releases.
- `Rebuild/Features/` contains the portable host presets.
  `Rebuild/Scripts/install-features.py` upgrades existing installations, with
  Mac writes directed to user settings so the signed app is preserved.
- `MODS.md` documents manual upgrades, mode commands, server bookmarks,
  authenticated GoldSrc joining and separate classic plugin-server installation.
- `WORK_STATE.json` is the portable local task state when the memory tools are
  unavailable. It is intentionally excluded from Git and release checksums.

## Making a release

Build into new temporary work/output directories; do not clobber an existing
release while building. Verify the new result, then replace the published
packages. Preserve framework/runtime symlinks and executable permissions.
Mac apps must be signed after all bundle edits and zipped using `ditto`.
Update the content manifest when shared game content changes. Keep the copied
scripts, README, manifest and verification report in `Rebuild/` synchronized,
regenerate `Rebuild-Kit.zip` without caches, then refresh `SHA256SUMS.txt`.
Update `AGENT_CONTEXT.md` with the final result and any remaining work.

Use claude-mem work_state tools for task tracking when available; this handoff
is the portable project context when those tools are unavailable. Do not assume
previous runtime tests cover newly modified binaries or claim graphical/LAN
testing from headless checks. Do not delete user settings without a current
request. The cleanup command moves known game apps/settings to Trash and should
only be run when the user intends a clean installation.
