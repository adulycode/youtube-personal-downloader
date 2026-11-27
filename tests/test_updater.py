import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('github_update',SOURCE/'native/github_update.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)

class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.stage = Path(self.temp.name)
        self.current = json.loads((SOURCE/'extension/manifest.json').read_text(encoding='utf-8-sig'))
        self.current['version'] = '1.2.0'

    def bundle(self, extra=None, mutate=None):
        content = {name:(SOURCE/name).read_bytes() for name in updater.FILES}
        if mutate: mutate(content)
        archive=self.stage/'YouTube-Downloader.zip'
        with zipfile.ZipFile(archive,'w') as z:
            for name,data in content.items(): z.writestr('YouTube-Downloader/'+name,data)
            if extra: z.writestr(extra,b'bad')
        checksum=self.stage/'SHA256SUMS.txt'
        checksum.write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  YouTube-Downloader.zip\n',encoding='utf-8')
        return archive,checksum

    def test_valid_bundle(self):
        content=updater.validate_bundle(*self.bundle(),self.current,'v1.6.6')
        self.assertEqual(set(content),set(updater.FILES))

    def test_checksum_mismatch(self):
        archive,checksum=self.bundle()
        archive.write_bytes(archive.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'checksum mismatch'):
            updater.validate_bundle(archive,checksum,self.current,'v1.6.6')

    def test_unexpected_path_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unexpected package'):
            updater.validate_bundle(*self.bundle(extra='../../outside.txt'),self.current,'v1.6.6')

    def test_identity_mismatch_rejected(self):
        def mutate(content):
            m=json.loads(content['extension/manifest.json']);m['key']='different'
            content['extension/manifest.json']=json.dumps(m).encode()
        with self.assertRaisesRegex(ValueError,'identity differs'):
            updater.validate_bundle(*self.bundle(mutate=mutate),self.current,'v1.6.6')

    def test_tag_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'version mismatch'):
            updater.validate_bundle(*self.bundle(),self.current,'v9.0.0')

    def test_preserves_environment(self):
        content=updater.validate_bundle(*self.bundle(),self.current,'v1.6.6')
        root=self.stage/'install'
        venv=root/'native/venv/keep.txt';venv.parent.mkdir(parents=True);venv.write_text('keep')
        with patch.object(updater,'ROOT',root):updater.apply_bundle(content)
        self.assertEqual(venv.read_text(),'keep')
        self.assertEqual((root/'extension/content.js').read_bytes(),content['extension/content.js'])

    def test_rolls_back_failed_write(self):
        content=updater.validate_bundle(*self.bundle(),self.current,'v1.6.6')
        root=self.stage/'install'
        originals={}
        for name in updater.FILES:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'old:'+name.encode());originals[name]=p.read_bytes()
        original_write=Path.write_bytes
        failed=False
        def write(p,data):
            nonlocal failed
            if p==root/'extension/popup.js' and not failed:
                failed=True
                raise OSError('simulated disk failure')
            return original_write(p,data)
        with patch.object(updater,'ROOT',root),patch.object(Path,'write_bytes',write):
            with self.assertRaises(OSError):updater.apply_bundle(content)
        for name,data in originals.items():self.assertEqual((root/name).read_bytes(),data)

    def test_no_new_version_does_not_download(self):
        release=json.dumps({'tag_name':'v1.6.6'}).encode()
        with patch.object(updater,'public_get',return_value=release) as request:
            result=updater.check_update()
        self.assertFalse(result['updated']);self.assertEqual(request.call_count,1)

if __name__=='__main__':unittest.main()
