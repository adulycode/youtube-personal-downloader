"""Build an offline Windows installer from vendor archives pinned by SHA-256."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
import zipfile
from package import ROOT, FILES, build

def build_setup():
    build()
    cache=Path(os.environ.get('SETUP_CACHE',ROOT/'work'/'setup-cache')).resolve()
    cache.mkdir(parents=True,exist_ok=True)
    installer=(ROOT/'native/install.ps1').read_text(encoding='utf-8-sig')
    dependencies=re.findall(r"Name='([^']+)';Url='([^']+)';Hash='([0-9a-f]{64})'",installer)
    if len(dependencies)!=4:raise ValueError('Expected four pinned setup dependencies')
    def download(item):
        name,url,expected=item
        target=cache/name
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            request=urllib.request.Request(url,headers={'User-Agent':'YouTubeDownloaderSetupBuilder'})
            with urllib.request.urlopen(request,timeout=180) as response,target.open('wb') as output:
                while data:=response.read(1024*1024):output.write(data)
        if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:raise ValueError('Dependency checksum mismatch: '+name)
        return target
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        archives=list(pool.map(download,dependencies))
    staging=ROOT/'work'/'setup-build'
    staging.mkdir(parents=True,exist_ok=True)
    payload=staging/'payload.zip'
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_STORED) as bundle:
        for name in FILES:bundle.write(ROOT/name,name)
        for archive in archives:bundle.write(archive,'setup-cache/'+archive.name)
    compiler=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    output=ROOT/'dist'/'YouTube-Downloader-Setup.exe'
    subprocess.run([str(compiler),'/nologo','/target:exe','/platform:x64','/optimize+',
                    '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll',
                    '/resource:'+str(payload)+',payload.zip','/out:'+str(output),str(ROOT/'scripts/Setup.cs')],check=True)
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    (ROOT/'dist'/'Setup-SHA256.txt').write_text(digest+'  '+output.name+'\n',encoding='utf-8')
    print('Built '+str(output)+' ('+str(output.stat().st_size)+' bytes)')

if __name__=='__main__':build_setup()
