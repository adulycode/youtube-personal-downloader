$ErrorActionPreference = 'Stop'
$registryPath = 'HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.personal.youtube_downloader'
if (Test-Path -LiteralPath $registryPath) { Remove-Item -LiteralPath $registryPath }
Write-Host 'Native host unregistered. Remove the extension in chrome://extensions. Downloaded files are preserved.'
