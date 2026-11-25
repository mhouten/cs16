# Publish a release

1. Commit/push the source to `git@github.com:mhouten/cs16.git` on `main`.
2. Place the verified Windows, Linux and Mac archives in the project root,
   beside `Rebuild-Kit.zip`, `Optional-Features.zip`, `MODS.md`, `SHA256SUMS.txt`,
   `VERIFICATION.json` and the cleanup command.
3. Authenticate and upload:

   ```sh
   gh auth login --hostname github.com --git-protocol ssh --web
   python3 Rebuild/Scripts/publish-release.py --repo mhouten/cs16 --tag v2026.11.25
   ```

The script checks local hashes, creates a draft release, uploads **all three** OS
packages and supporting assets, and checks GitHub's asset digests before
publishing it as the latest release. Rerun with the same tag and target to resume
an interrupted draft upload. Use `--target COMMIT` to tag a specific pushed commit.
Use a new tag for a new version. Large archives belong in Releases and are
ignored by Git. Keep README download filenames stable. After publishing, check
that each public `releases/latest/download/` URL in the README serves its asset.

## Linux portability gate

Run the manually dispatched **Linux release runtime validation** workflow for
the release commit. Build the full packages locally from authorized source
data using the README. The Linux packager audits the staged tree before
creating the tar.gz and writes an archive SHA-256. The publisher checks the
assembled release checksums and independently audits the tar.gz before any
release operation. Use Python 3.12+ and GNU binutils on the publishing host.

Keep the locked Linux source/resource inputs and ELF report with the release
verification evidence. The GitHub workflow has read-only repository access
and runs asset-free runtime validation. Publication requires a
separately authorized invocation of the release script with a new explicit tag.
The local Linux candidate and its rebuild kit are staged under
`build/linux-portability/release/`. Use that candidate's verification evidence
when preparing the next complete release set.
