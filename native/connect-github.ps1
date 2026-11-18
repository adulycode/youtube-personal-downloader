$ErrorActionPreference = 'Stop'
$ghCommand = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghCommand) {
    $knownPath = Join-Path $env:ProgramFiles 'GitHub CLI\gh.exe'
    if (Test-Path -LiteralPath $knownPath) { $ghPath = $knownPath }
    else {
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Install GitHub CLI from https://cli.github.com first.' }
        & winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI installation failed.' }
        $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
        $ghPath = (Get-Command gh -ErrorAction Stop).Source
    }
} else { $ghPath = $ghCommand.Source }
& $ghPath auth status --hostname github.com
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Sign in with your own GitHub account that has access to the private repository.'
    & $ghPath auth login --hostname github.com --git-protocol https --web
    if ($LASTEXITCODE -ne 0) { throw 'GitHub sign-in not completed.' }
}
& $ghPath repo view adulycode/youtube-personal-downloader --json nameWithOwner
if ($LASTEXITCODE -ne 0) { throw 'Your GitHub account needs access to this private repository first.' }
Write-Host 'Connected. Reload the extension once. Future updates are checked automatically every 6 hours.'
