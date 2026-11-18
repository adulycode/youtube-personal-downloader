import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('host',SOURCE/'native/host.py')
host=importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)

class HostRuntimeTests(unittest.TestCase):
    def command(self,root):
        with patch.object(host,'ROOT',root),patch.object(host,'tool',side_effect=lambda n:str(root/'tools'/(n+'.exe'))):
            return host.build_command({'url':'https://www.youtube.com/shorts/1Ujb6FTm59I','format':'mp3','quality':1080})

    def test_new_install_uses_bundled_executable(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'tools').mkdir();(root/'tools/yt-dlp.exe').touch()
            command=self.command(root)
            self.assertEqual(command[0],str(root/'tools/yt-dlp.exe'))
            self.assertNotIn('-m',command)
            self.assertIn('--audio-format',command)

    def test_existing_install_keeps_python_module(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.command(Path(folder))[:3],[sys.executable,'-m','yt_dlp'])

if __name__=='__main__':unittest.main()
