# YouTube Personal Downloader

Private source for the Windows Chrome extension. Read [Thai installation instructions](README-TH.md).

## Release pipeline

Every push to `main` affecting source runs syntax checks and builds an allowlisted ZIP with SHA-256 checksums. A new `extension/manifest.json` version creates a new private GitHub Release. Existing releases are preserved. No personal token, virtual environment, tool binaries, or machine-specific registry manifest is packaged.

The workflow uses the repository's ephemeral `GITHUB_TOKEN` with `contents: write`. No personal token secret is needed for publishing. GitHub Actions must be enabled for this repository.

## Current update behavior

`UPDATE.cmd` bootstraps this version from an extracted ZIP and restores the original registered path when needed. Reload the extension once after that bootstrap. Run `CONNECT-GITHUB.cmd` once per Windows account to authenticate GitHub CLI using an account with access to this private repository. Connecting this repository to Codex does not authenticate users' extension installations. Do not distribute the owner's token.

After setup, the extension checks stable private Releases every six hours while Chrome is running. A popup button can check immediately. The helper downloads a pinned release tag through GitHub CLI, checks the archive SHA-256, exact package allowlist, version and extension identity, preserves the Python environment and native registration, and rolls back file writes on an error. The extension reloads itself after applying updates. Refresh open YouTube pages to use new content scripts. There is no Windows scheduled task or background service. This setup does not automatically migrate external dependencies or registry schemas.

The updater runs code published by the repository owner. Only trusted maintainers should have write access. SHA-256 verifies package integrity; it is not an independent publisher signature. Tests use local fixtures; a live private-release client update still requires a GitHub-authenticated Windows installation.

Build locally with `python scripts/package.py`. Outputs are in `dist/`.
