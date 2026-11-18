param([string]$ExtensionId,[string]$InstallRoot,[string]$BundleCache,[switch]$SkipRegistration,[switch]$NoOpen)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
if(-not [Environment]::Is64BitOperatingSystem){throw '64-bit Windows 10 or 11 is required.'}
$sourceRoot=Split-Path -Parent $PSScriptRoot
if(-not $ExtensionId){$ExtensionId=(Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'extension-id.txt')).Trim()}
if($ExtensionId -cnotmatch '^[a-p]{32}$'){throw 'Invalid extension identity.'}
$registryPath='HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.personal.youtube_downloader'
if(-not $InstallRoot){
    $InstallRoot=Join-Path $env:LOCALAPPDATA 'YouTubePersonalDownloader'
    if(Test-Path -LiteralPath $registryPath){
        $registered=(Get-Item -LiteralPath $registryPath).GetValue('')
        if($registered -and [IO.Path]::IsPathRooted($registered)){
            $previous=Split-Path -Parent (Split-Path -Parent $registered)
            $oldManifest=Join-Path $previous 'extension\manifest.json'
            if(Test-Path -LiteralPath $oldManifest){
                $old=Get-Content -Raw -LiteralPath $oldManifest|ConvertFrom-Json
                $new=Get-Content -Raw -LiteralPath (Join-Path $sourceRoot 'extension\manifest.json')|ConvertFrom-Json
                if($old.key -eq $new.key){$InstallRoot=$previous}
            }
        }
    }
}
$InstallRoot=[IO.Path]::GetFullPath($InstallRoot)
$nativeRoot=Join-Path $InstallRoot 'native'
$toolsRoot=Join-Path $nativeRoot 'tools'
$runtimeRoot=Join-Path $nativeRoot 'runtime'
New-Item -ItemType Directory -Path $toolsRoot,$runtimeRoot -Force|Out-Null
if(-not $BundleCache){$BundleCache=Join-Path $sourceRoot 'setup-cache'}
$cacheRoot=if(Test-Path -LiteralPath $BundleCache){$BundleCache}else{Join-Path $nativeRoot 'setup-cache'}
New-Item -ItemType Directory -Path $cacheRoot -Force|Out-Null
$dependencies=@(
 @{Name='python.zip';Url='https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip';Hash='90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'},
 @{Name='yt-dlp.exe';Url='https://github.com/yt-dlp/yt-dlp/releases/download/2026.10.26/yt-dlp.exe';Hash='f5389d3698ecde4ef06f4e6b1ce0294fe9ac1396228c8990b8d3416d6d177a7d'},
 @{Name='ffmpeg.zip';Url='https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip';Hash='60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba'},
 @{Name='deno.zip';Url='https://github.com/denoland/deno/releases/download/v2.9.8/deno-x86_64-pc-windows-msvc.zip';Hash='cba84b26e0df5ae7f74fc66b86a95b866872a86292ebd84fa1e959927edd93bf'}
)
Add-Type -AssemblyName System.IO.Compression.FileSystem
$number=0
foreach($dependency in $dependencies){
    $number++;Write-Host "[$number/4] Preparing $($dependency.Name)..."
    $archive=Join-Path $cacheRoot $dependency.Name
    $valid=(Test-Path -LiteralPath $archive) -and ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -eq $dependency.Hash)
    if(-not $valid){
        $downloadPath=$archive+'.download'
        for($attempt=1;$attempt -le 3;$attempt++){
            try{
                Invoke-WebRequest -Uri $dependency.Url -OutFile $downloadPath -UseBasicParsing -TimeoutSec 300
                if((Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash -ne $dependency.Hash){throw 'Download checksum mismatch.'}
                Move-Item -LiteralPath $downloadPath -Destination $archive -Force
                break
            }catch{if($attempt -eq 3){throw}}
        }
    }
    if($dependency.Name -eq 'python.zip'){
        Expand-Archive -LiteralPath $archive -DestinationPath $runtimeRoot -Force
        [IO.File]::WriteAllText((Join-Path $runtimeRoot 'python314._pth'),"python314.zip`r`n.`r`n..`r`n",[Text.Encoding]::ASCII)
    }elseif($dependency.Name -eq 'yt-dlp.exe'){
        Copy-Item -LiteralPath $archive -Destination (Join-Path $toolsRoot 'yt-dlp.exe') -Force
    }else{
        $zip=[IO.Compression.ZipFile]::OpenRead($archive)
        try{foreach($entry in $zip.Entries){
            if($entry.Name -in @('ffmpeg.exe','ffprobe.exe','deno.exe')){[IO.Compression.ZipFileExtensions]::ExtractToFile($entry,(Join-Path $toolsRoot $entry.Name),$true)}
            if($entry.Name -match '^(LICENSE|COPYING)(\.txt|\.md|\.LGPLv3|\.GPLv3)?$'){
                $licenses=Join-Path $toolsRoot 'licenses';New-Item -ItemType Directory -Path $licenses -Force|Out-Null
                [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,(Join-Path $licenses ($dependency.Name+'-'+$entry.Name)),$true)
            }
        }}finally{$zip.Dispose()}
    }
}
if($InstallRoot.TrimEnd('\') -ne [IO.Path]::GetFullPath($sourceRoot).TrimEnd('\')){
    $extensionRoot=Join-Path $InstallRoot 'extension';New-Item -ItemType Directory -Path $extensionRoot -Force|Out-Null
    Get-ChildItem -LiteralPath (Join-Path $sourceRoot 'extension') -File|ForEach-Object{Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $extensionRoot $_.Name) -Force}
    foreach($name in @('host.py','github_update.py','install.ps1','update.ps1','uninstall.ps1','connect-github.ps1','extension-id.txt')){Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $nativeRoot $name) -Force}
    foreach($name in @('INSTALL.cmd','UPDATE.cmd','CONNECT-GITHUB.cmd','README-TH.md')){Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination (Join-Path $InstallRoot $name) -Force}
}
$pythonPath=Join-Path $runtimeRoot 'python.exe'
& $pythonPath -c 'import sys,json,ssl,struct; import github_update; print(sys.version.split()[0])'
if($LASTEXITCODE -ne 0){throw 'Bundled Python verification failed.'}
foreach($tool in @(@{Name='yt-dlp.exe';Arg='--version'},@{Name='ffmpeg.exe';Arg='-version'},@{Name='ffprobe.exe';Arg='-version'},@{Name='deno.exe';Arg='--version'})){
    $toolOutput=& (Join-Path $toolsRoot $tool.Name) $tool.Arg 2>&1
    if($LASTEXITCODE -ne 0){throw ('Tool verification failed: '+$tool.Name)}
    Write-Host ([string]($toolOutput|Select-Object -First 1))
}
$launcher=Join-Path $nativeRoot 'host.cmd'
[IO.File]::WriteAllText($launcher,('@echo off'+"`r`n"+'"%~dp0runtime\python.exe" "%~dp0host.py"'+"`r`n"),[Text.Encoding]::ASCII)
$manifestPath=Join-Path $nativeRoot 'com.personal.youtube_downloader.json'
$manifest=@{name='com.personal.youtube_downloader';description='YouTube Personal Downloader';path=$launcher;type='stdio';allowed_origins=@("chrome-extension://$ExtensionId/")}
[IO.File]::WriteAllText($manifestPath,($manifest|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
if(-not $SkipRegistration){New-Item -Path $registryPath -Force|Out-Null;Set-Item -LiteralPath $registryPath -Value $manifestPath}
Write-Host ''
Write-Host 'SUCCESS - All helper programs are installed and verified.' -ForegroundColor Green
$extensionFolder=Join-Path $InstallRoot 'extension'
Write-Host ('Extension folder: '+$extensionFolder)
Write-Host 'Chrome: Developer mode > Load unpacked > paste the extension folder.'
Write-Host 'Already installed? Click Reload on the existing extension instead.'
Write-Host 'No system Python, Microsoft Store, winget or GitHub login is required.'
if(-not $NoOpen){
    try{Set-Clipboard -Value $extensionFolder}catch{}
    Start-Process explorer.exe -ArgumentList ('"'+$extensionFolder+'"')
    $chromePaths=@((Join-Path ${env:ProgramFiles} 'Google\Chrome\Application\chrome.exe'),(Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),(Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe'))
    $chromePath=$chromePaths|Where-Object{Test-Path -LiteralPath $_}|Select-Object -First 1
    if($chromePath){Start-Process -FilePath $chromePath -ArgumentList 'chrome://extensions'}
}
