"""Public release updates without GitHub accounts or tokens."""
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

REPOSITORY = 'adulycode/youtube-personal-downloader'
ROOT = Path(__file__).resolve().parent.parent
FILES = (
    'extension/manifest.json', 'extension/background.js', 'extension/popup.html',
    'extension/popup.js', 'extension/style.css', 'extension/content.js',
    'extension/video-url.js', 'INSTALL.cmd', 'UPDATE.cmd', 'README-TH.md',
    'native/host.py', 'native/install.ps1', 'native/uninstall.ps1',
    'native/update.ps1', 'native/extension-id.txt', 'native/github_update.py',
    'CONNECT-GITHUB.cmd', 'native/connect-github.ps1',
)

def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?',value):
        raise ValueError('Invalid release version')
    parts = tuple(int(x) for x in value.split('.'))
    if any(x > 65535 for x in parts):
        raise ValueError('Invalid release version')
    return parts + (0,) * (4 - len(parts))

def public_get(url, limit=10_000_000):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('api.github.com','github.com'):
        raise ValueError('Invalid update URL')
    request = Request(url, headers={'User-Agent':'YouTube-Personal-Downloader','Accept':'application/vnd.github+json' if parsed.hostname == 'api.github.com' else 'application/octet-stream'})
    with urlopen(request, timeout=60) as response:
        if urlsplit(response.url).scheme != 'https':
            raise ValueError('Invalid download redirect')
        data = response.read(limit+1)
    if len(data) > limit:
        raise ValueError('Update response too large')
    return data

def validate_bundle(archive, checksum, current, tag):
    expected = checksum.read_text(encoding='utf-8').strip().splitlines()
    if len(expected) != 1 or not re.fullmatch(r'[0-9a-fA-F]{64}\s+YouTube-Downloader\.zip',expected[0]):
        raise ValueError('Invalid checksum file')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected[0].split()[0].lower():
        raise ValueError('ZIP checksum mismatch')
    with zipfile.ZipFile(archive) as bundle:
        prefix = 'YouTube-Downloader/'
        names = [prefix + name for name in FILES]
        if len(bundle.namelist()) != len(names) or set(bundle.namelist()) != set(names):
            raise ValueError('Unexpected package contents')
        if sum(item.file_size for item in bundle.infolist()) > 10_000_000:
            raise ValueError('Update package too large')
        content = {name:bundle.read(prefix+name) for name in FILES}
    incoming = json.loads(content['extension/manifest.json'].decode('utf-8-sig'))
    if incoming.get('key') != current.get('key') or not incoming.get('key'):
        raise ValueError('Update extension identity differs')
    if 'v'+incoming['version'] != tag or version(incoming['version']) <= version(current['version']):
        raise ValueError('Update version mismatch')
    digest = hashlib.sha256(base64.b64decode(incoming['key'])).hexdigest()[:32]
    expected_id = ''.join(chr(97+int(c,16)) for c in digest)
    if content['native/extension-id.txt'].decode().strip() != expected_id:
        raise ValueError('Update extension ID mismatch')
    return content

def apply_bundle(content):
    # Preserve the Python environment, downloaded media, host registration.
    with tempfile.TemporaryDirectory(prefix='yt-update-backup-') as temporary:
        backups = {}
        changed = []
        for name in FILES:
            target = ROOT/name
            if target.exists():
                backup = Path(temporary)/name
                backup.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(target,backup)
                backups[name] = backup
        try:
            # Manifest last: the extension version advances only after other files are written.
            order = [n for n in FILES if n != 'extension/manifest.json'] + ['extension/manifest.json']
            for name in order:
                target = ROOT/name
                target.parent.mkdir(parents=True,exist_ok=True)
                changed.append(name)
                target.write_bytes(content[name])
        except Exception:
            for name in reversed(changed):
                target = ROOT/name
                if name in backups:
                    shutil.copy2(backups[name],target)
                else:
                    target.unlink(missing_ok=True)
            raise

def check_update():
    current = json.loads((ROOT/'extension/manifest.json').read_text(encoding='utf-8-sig'))
    release = json.loads(public_get(f'https://api.github.com/repos/{REPOSITORY}/releases/latest',1_000_000))
    tag = release.get('tag_name','')
    if not tag.startswith('v'):
        raise ValueError('Invalid release tag')
    if version(tag[1:]) <= version(current['version']):
        return {'updated':False,'message':'เป็นเวอร์ชันล่าสุดแล้ว ('+current['version']+')'}
    if release.get('draft') or release.get('prerelease'):
        raise ValueError('Not a stable release')
    with tempfile.TemporaryDirectory(prefix='yt-update-') as temporary:
        stage = Path(temporary)
        for name in ('YouTube-Downloader.zip','SHA256SUMS.txt'):
            url = f'https://github.com/{REPOSITORY}/releases/download/{tag}/{name}'
            (stage/name).write_bytes(public_get(url,10_000_000 if name.endswith('.zip') else 4096))
        archive = stage/'YouTube-Downloader.zip'
        if archive.stat().st_size > 10_000_000:
            raise ValueError('Update package too large')
        content = validate_bundle(archive,stage/'SHA256SUMS.txt',current,tag)
        apply_bundle(content)
    return {'updated':True,'message':'อัปเดตเป็น '+tag+' แล้ว กำลังโหลดส่วนขยายใหม่'}
