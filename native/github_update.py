"""Private release updates authenticated through the user's GitHub CLI session."""
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

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

def gh_cli():
    candidate = shutil.which('gh')
    if not candidate:
        import os
        candidate = str(Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'GitHub CLI'/'gh.exe')
        if not Path(candidate).is_file():
            raise ValueError('เปิด CONNECT-GITHUB.cmd ครั้งแรกเพื่อเชื่อมระบบอัปเดต')
    return candidate

def gh(*args):
    result = subprocess.run([gh_cli(),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                            timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        # Do not return arbitrary CLI diagnostics that might include authentication data.
        raise ValueError('เข้าถึง private release ไม่ได้: เปิด CONNECT-GITHUB.cmd และตรวจสิทธิ์ repo')
    return result.stdout

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
    # Preserve the Python environment, downloaded media, host registration and CLI login.
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
    release = json.loads(gh('api',f'repos/{REPOSITORY}/releases/latest'))
    tag = release.get('tag_name','')
    if not tag.startswith('v'):
        raise ValueError('Invalid release tag')
    if version(tag[1:]) <= version(current['version']):
        return {'updated':False,'message':'เป็นเวอร์ชันล่าสุดแล้ว ('+current['version']+')'}
    if release.get('draft') or release.get('prerelease'):
        raise ValueError('Not a stable release')
    with tempfile.TemporaryDirectory(prefix='yt-update-') as temporary:
        stage = Path(temporary)
        gh('release','download',tag,'--repo',REPOSITORY,'--pattern','YouTube-Downloader.zip',
           '--pattern','SHA256SUMS.txt','--dir',str(stage))
        archive = stage/'YouTube-Downloader.zip'
        if archive.stat().st_size > 10_000_000:
            raise ValueError('Update package too large')
        content = validate_bundle(archive,stage/'SHA256SUMS.txt',current,tag)
        apply_bundle(content)
    return {'updated':True,'message':'อัปเดตเป็น '+tag+' แล้ว กำลังโหลดส่วนขยายใหม่'}
