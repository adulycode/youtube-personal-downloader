# YouTube Personal Downloader

Chrome extension and Windows helper. Read README-TH.md for installation.

Version 1.4 uses public GitHub Releases over HTTPS. Client machines need no GitHub account, CLI or token. Updates are checked every six hours while Chrome runs, or immediately from the popup. After applying an update the extension reloads itself. Refresh open YouTube pages for updated content scripts.

Existing users: run UPDATE.cmd from the latest package then reload the extension once. New users: run INSTALL.cmd then load the extension folder in chrome://extensions with Developer mode. Keep the installation folder in place. CONNECT-GITHUB.cmd remains for compatibility and no longer authenticates or installs anything.

Source pushes to main run tests and package an explicit allowlist with SHA-256 checksums. Increase extension/manifest.json version to publish a new Release; existing releases are preserved. Build using python scripts/package.py.

The updater checks checksum, paths, version and extension identity, and rolls back failed writes. It preserves the Python environment and native registration. External dependency/schema migrations may require separate setup. SHA-256 is an integrity check, not an independent publisher signature. Only trusted maintainers should publish releases.

Credentials, local dependencies and machine-specific manifests are excluded. Content script layout and real YouTube downloading still need live verification.
