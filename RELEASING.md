# Publish a release

1. Commit/push the source to `git@github.com:mhouten/cs16.git` on `main`.
2. Place the verified Windows, Linux and Mac archives in the project root,
   beside `Rebuild-Kit.zip`, `SHA256SUMS.txt`, `VERIFICATION.json` and the cleanup command.
3. Authenticate and upload:

   ```sh
   gh auth login --hostname github.com --git-protocol ssh --web
   python3 Rebuild/Scripts/publish-release.py --repo mhouten/cs16 --tag v2026.10.31
   ```

The script checks hashes, creates a draft release, uploads **all three** OS
packages and supporting assets, then publishes it as the latest release.
Use a new tag for a new version. Large archives belong in Releases and are
ignored by Git. Keep README download filenames stable.
