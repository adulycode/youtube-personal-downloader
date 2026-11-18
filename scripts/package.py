"""Build a distribution from an explicit allowlist; never bundle local credentials."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'extension/manifest.json', 'extension/background.js', 'extension/popup.html',
    'extension/popup.js', 'extension/style.css', 'extension/content.js',
    'extension/video-url.js', 'INSTALL.cmd', 'UPDATE.cmd', 'README-TH.md',
    'native/host.py', 'native/install.ps1', 'native/uninstall.ps1',
    'native/update.ps1', 'native/extension-id.txt', 'native/github_update.py',
    'CONNECT-GITHUB.cmd', 'native/connect-github.ps1',
]

def build():
    manifest = json.loads((ROOT / 'extension/manifest.json').read_text(encoding='utf-8-sig'))
    version = manifest['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?', version):
        raise ValueError('Invalid extension version')
    import base64
    digest = hashlib.sha256(base64.b64decode(manifest['key'])).hexdigest()[:32]
    expected = ''.join(chr(97 + int(c,16)) for c in digest)
    if (ROOT / 'native/extension-id.txt').read_text().strip() != expected:
        raise ValueError('Extension ID does not match manifest key')
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / 'YouTube-Downloader.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in FILES:
            bundle.write(ROOT / name, 'YouTube-Downloader/' + name)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('Invalid ZIP')
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'SHA256SUMS.txt').write_text(f'{sha}  {archive.name}\n',encoding='utf-8')
    (output/'version.json').write_text(json.dumps({'version':version,'file':archive.name,'sha256':sha},indent=2)+'\n',encoding='utf-8')
    print(version)

if __name__ == '__main__':
    build()
