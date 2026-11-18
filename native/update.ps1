param([string]$RegisteredManifestPath)
$ErrorActionPreference = 'Stop'
$registryPath = 'HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.personal.youtube_downloader'
if ($RegisteredManifestPath) { $manifestPath = $RegisteredManifestPath }
else {
    if (-not (Test-Path -LiteralPath $registryPath)) { throw 'First installation required: run INSTALL.cmd once.' }
    $manifestPath = (Get-Item -LiteralPath $registryPath).GetValue('')
}
if (-not [IO.Path]::IsPathRooted($manifestPath) -or (Split-Path -Leaf $manifestPath) -ne 'com.personal.youtube_downloader.json') { throw 'Invalid registered native host path.' }
$installedNative = Split-Path -Parent $manifestPath
$installedRoot = Split-Path -Parent $installedNative
$sourceRoot = Split-Path -Parent $PSScriptRoot
$installedExtension = Join-Path $installedRoot 'extension'
$incoming = Get-Content -Raw -LiteralPath (Join-Path $sourceRoot 'extension\manifest.json') | ConvertFrom-Json
if (Test-Path -LiteralPath (Join-Path $installedExtension 'manifest.json')) {
    $existing = Get-Content -Raw -LiteralPath (Join-Path $installedExtension 'manifest.json') | ConvertFrom-Json
    if ($existing.key -ne $incoming.key) { throw 'Extension keys differ. Update stopped to preserve the installed ID.' }
} else {
    Write-Host 'Original extension folder is missing. Restoring files to its registered location...'
}
if (Test-Path -LiteralPath $manifestPath) {
    $nativeConfig = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $expectedId = (Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'extension-id.txt')).Trim()
    if (@($nativeConfig.allowed_origins) -notcontains "chrome-extension://$expectedId/") { throw 'Registered extension ID differs. Update stopped.' }
}
New-Item -ItemType Directory -Path $installedExtension -Force | Out-Null
New-Item -ItemType Directory -Path $installedNative -Force | Out-Null
if ([IO.Path]::GetFullPath($installedRoot).TrimEnd('\') -ne [IO.Path]::GetFullPath($sourceRoot).TrimEnd('\')) {
    Get-ChildItem -LiteralPath (Join-Path $sourceRoot 'extension') -File | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $installedExtension $_.Name) -Force
    }
    foreach ($file in @('host.py','install.ps1','uninstall.ps1','update.ps1','extension-id.txt','github_update.py','connect-github.ps1')) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination (Join-Path $installedNative $file) -Force
    }
    Copy-Item -LiteralPath (Join-Path $sourceRoot 'CONNECT-GITHUB.cmd') -Destination (Join-Path $installedRoot 'CONNECT-GITHUB.cmd') -Force
}
$venvPython = Join-Path $installedNative 'venv\Scripts\python.exe'
$bundledPython = Join-Path $installedNative 'runtime\python.exe'
if ((-not (Test-Path -LiteralPath $venvPython) -and -not (Test-Path -LiteralPath $bundledPython)) -or -not (Test-Path -LiteralPath (Join-Path $installedNative 'host.cmd')) -or -not (Test-Path -LiteralPath $manifestPath)) {
    Write-Host 'Some helper files were moved or removed. Repairing them automatically (internet may be required)...'
    & (Join-Path $installedNative 'install.ps1') -InstallRoot $installedRoot
}
Write-Host 'Updated in place. No reinstall or Extension ID entry needed.'
Write-Host 'Open chrome://extensions, click Reload on YouTube Personal Downloader, then refresh YouTube.'
Write-Host 'Always load the original extension folder, not the folder containing this update ZIP.'
