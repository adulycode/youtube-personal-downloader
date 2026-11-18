param([string]$ExtensionId)
$ErrorActionPreference = 'Stop'
if (-not $ExtensionId) { $ExtensionId = (Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'extension-id.txt')).Trim() }
if ($ExtensionId -cnotmatch '^[a-p]{32}$') { throw 'Invalid Chrome Extension ID' }
foreach ($dependency in @(@{Command='python'; Package='Python.Python.3.12'}, @{Command='ffmpeg'; Package='Gyan.FFmpeg'}, @{Command='ffprobe'; Package='Gyan.FFmpeg'}, @{Command='deno'; Package='DenoLand.Deno'})) {
    $localTool = Join-Path $PSScriptRoot ('tools\' + $dependency.Command + '.exe')
    if (-not (Get-Command $dependency.Command -ErrorAction SilentlyContinue) -and -not (Test-Path -LiteralPath $localTool)) {
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Missing dependency and winget unavailable. See README-TH.md for manual installation.' }
        Write-Host ('Installing ' + $dependency.Package)
        & winget install --id $dependency.Package -e --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) { throw ('Unable to install ' + $dependency.Package + '. See README-TH.md') }
        $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
    }
}
$pythonCommand = Get-Command python -ErrorAction Stop
$pythonPath = & $pythonCommand.Source -c 'import sys; print(sys.executable)'
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.10+ from https://www.python.org/downloads/windows/ first' }
$venvPath = Join-Path $PSScriptRoot 'venv'
& $pythonPath -m venv $venvPath
if ($LASTEXITCODE -ne 0) { throw 'Unable to create Python environment' }
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
& $venvPython -m pip install --upgrade 'yt-dlp[default]'
if ($LASTEXITCODE -ne 0) { throw 'Unable to install yt-dlp' }
$launcher = Join-Path $PSScriptRoot 'host.cmd'
$hostScript = Join-Path $PSScriptRoot 'host.py'
# cmd expands percent signs even inside quotes. Reject unusual install paths.
if (($venvPython + $hostScript).Contains('%')) { throw 'Move this folder to a path without percent signs' }
$launcherText = '@echo off' + "`r`n" + '"' + $venvPython + '" "' + $hostScript + '"' + "`r`n"
[IO.File]::WriteAllText($launcher,$launcherText,[Text.Encoding]::Default)
$manifestPath = Join-Path $PSScriptRoot 'com.personal.youtube_downloader.json'
$manifest = @{name='com.personal.youtube_downloader';description='Personal YouTube downloader';path=$launcher;type='stdio';allowed_origins=@("chrome-extension://$ExtensionId/")}
[IO.File]::WriteAllText($manifestPath,($manifest | ConvertTo-Json),[Text.UTF8Encoding]::new($false))
$registryPath = 'HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.personal.youtube_downloader'
New-Item -Path $registryPath -Force | Out-Null
Set-Item -LiteralPath $registryPath -Value $manifestPath
Write-Host 'Native host registered for your Windows account. No administrator rights required.'
foreach ($toolName in @('ffmpeg','ffprobe','deno')) {
    $localTool = Join-Path $PSScriptRoot "tools\$toolName.exe"
    if (-not (Test-Path -LiteralPath $localTool) -and -not (Get-Command $toolName -ErrorAction SilentlyContinue)) {
        Write-Warning "Missing $toolName. Read README-TH.md before downloading."
    }
}
Write-Host 'Restart Chrome after installing dependencies. Keep this folder in its current location.'
