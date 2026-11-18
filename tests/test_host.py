import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import io
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
            self.assertIn('--progress',command)
            self.assertIn('--progress-delta',command)

    def test_existing_install_keeps_python_module(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.command(Path(folder))[:3],[sys.executable,'-m','yt_dlp'])

    def test_progress_speed_eta_processing_and_completion(self):
        class Process:
            stdout=io.StringIO('PROGRESS: 42.5%|2.5MiB/s|00:12\nPOSTPROCESS:started\nFILE:C:/Downloads/song.mp3\n')
            def poll(self):return 0
            def wait(self):return 0
        events=[]
        host.CANCEL.clear()
        with patch.object(host,'build_command',return_value=['fake']),patch.object(host.subprocess,'Popen',return_value=Process()) as popen,patch.object(host,'send',side_effect=lambda kind,message,**kw:events.append((kind,message,kw))):
            host.download({})
        self.assertEqual(popen.call_args.kwargs.get('stdin'),host.subprocess.DEVNULL)
        numeric=[event for event in events if event[2].get('percent')==42.5]
        self.assertEqual(len(numeric),1)
        self.assertIn('2.5MiB/s',numeric[0][1])
        self.assertIn('00:12',numeric[0][1])
        self.assertTrue(any(e[2].get('stage')=='processing' for e in events))
        self.assertEqual(events[-1][0],'done')

    def test_unknown_size_and_download_failure_are_reported(self):
        class Process:
            stdout=io.StringIO('PROGRESS: NA|NA|NA\nERROR: network unavailable\n')
            def poll(self):return 1
            def wait(self):return 1
        events=[]
        host.CANCEL.clear()
        with patch.object(host,'build_command',return_value=['fake']),patch.object(host.subprocess,'Popen',return_value=Process()),patch.object(host,'send',side_effect=lambda kind,message,**kw:events.append((kind,message,kw))):
            host.download({})
        self.assertTrue(any(e[2].get('stage')=='downloading' and 'percent' not in e[2] for e in events))
        self.assertEqual(events[-1][0],'error')

if __name__=='__main__':unittest.main()
