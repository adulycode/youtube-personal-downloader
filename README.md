# YouTube Personal Downloader

Windows 10/11 x64 Chrome extension and native helper. See README-TH.md.

New users open YouTube-Downloader-Setup.exe. It embeds the source and four vendor archives (about 194 MB) and installs a private Python runtime, standalone yt-dlp, FFmpeg/ffprobe and Deno. No system Python, Store alias, winget, PATH changes or GitHub login is required. It registers only the current user's native host. Chrome requires Developer mode and Load unpacked once; the installer opens that page, opens the extension folder and copies its path. This is not a silent Chrome extension installation. The executable is unsigned.

The offline package is built with scripts/build_setup.py on Windows using the system .NET Framework C# compiler. Downloads are pinned and verified by SHA-256. Run the built EXE with --test-root ABSOLUTE_PATH to test without registration or opening UI. Tests must use an isolated writable path. No global environment is changed.

Source pushes run tests, build an allowlisted update ZIP, and publish new manifest versions. A Windows job builds and tests the actual offline installer before attaching it to the same Release. Existing small ZIP clients remain supported because the update archive's 18-file allowlist is unchanged. Version 1.6 keeps the old pip/venv downloader fallback for existing installs.

Public updates need no account. Checks occur every six hours while Chrome runs or on request. Checksums, package paths, versions and extension identity are validated and failed writes are rolled back. Existing runtime, tools and registration are preserved. Binary dependencies are refreshed by running a newer Setup, not by code-only updates.

Third-party archives are redistributed unmodified inside the installer payload; see their notices and source/build links in README-TH.md. Installer caches and binaries are excluded from source control. The offline executable is a separate Release asset, not included in the normal update ZIP.
