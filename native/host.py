"""Windows Chrome native messaging host. stdout is reserved for framed JSON."""
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import threading
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parent
LOCK = threading.Lock()
CANCEL = threading.Event()

def send(kind, message, **extra):
    payload = json.dumps(dict(type=kind, message=message, **extra), ensure_ascii=False).encode('utf-8')
    with LOCK:
        sys.stdout.buffer.write(struct.pack('<I', len(payload)) + payload)
        sys.stdout.buffer.flush()

def canonical_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('Invalid YouTube URL')
    u = urlsplit(value)
    if u.scheme != 'https' or u.username or u.password or u.port not in (None,443):
        raise ValueError('Use an HTTPS YouTube video URL')
    host = u.hostname
    if host == 'youtu.be':
        video = u.path.strip('/')
    elif host in ('youtube.com','www.youtube.com','m.youtube.com','music.youtube.com'):
        if u.path == '/watch':
            video = parse_qs(u.query).get('v',[''])[0]
        else:
            match = re.fullmatch(r'/(?:shorts|live|embed)/([A-Za-z0-9_-]{11})/?',u.path)
            video = match.group(1) if match else ''
    else:
        raise ValueError('Only YouTube video links are accepted')
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}',video):
        raise ValueError('The URL must point to one YouTube video')
    return 'https://www.youtube.com/watch?v=' + video

def tool(name):
    local = ROOT / 'tools' / (name + '.exe')
    found = str(local) if local.is_file() else shutil.which(name)
    if not found:
        raise ValueError('Missing '+name+'. Install dependencies; see README-TH.md')
    return found

def build_command(request):
    url = canonical_url(request.get('url'))
    mode = request.get('format')
    if mode not in ('mp3','mp4'):
        raise ValueError('Invalid format')
    quality = request.get('quality',1080)
    if type(quality) is not int or quality not in (720,1080,2160):
        raise ValueError('Invalid quality')
    target = Path.home() / 'Downloads' / 'YouTube Personal'
    ffmpeg = tool('ffmpeg')
    tool('ffprobe')
    deno = tool('deno')
    standalone = ROOT / 'tools' / 'yt-dlp.exe'
    executable = [str(standalone)] if standalone.is_file() else [sys.executable,'-m','yt_dlp']
    command = executable + ['--ignore-config','--no-playlist','--no-overwrites',
               '--windows-filenames','--trim-filenames','160','--newline','--no-colors',
               '--progress','--progress-delta','0.5',
               '--progress-template','download:PROGRESS:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s',
               '--progress-template','postprocess:POSTPROCESS:%(progress.status)s',
               '--print','after_move:FILE:%(filepath)s','--no-simulate',
               '--ffmpeg-location',str(Path(ffmpeg).parent),'--js-runtimes','deno:'+deno,
               '-P',str(target),'-o','%(title)s [%(id)s].%(ext)s']
    if mode == 'mp3':
        command += ['-f','bestaudio/best','-x','--audio-format','mp3','--audio-quality','192K']
    else:
        command += ['-f',f'bv*[ext=mp4][height<={quality}]+ba[ext=m4a]/b[ext=mp4][height<={quality}]',
                    '--merge-output-format','mp4']
    return command + ['--',url]

def stop_process(proc):
    if proc.poll() is None:
        if os.name == 'nt':
            subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            proc.terminate()

def download(request):
    proc = None
    finished = threading.Event()
    try:
        command = build_command(request)
        send('progress','กำลังอ่านข้อมูลคลิปและเตรียมดาวน์โหลด…',stage='preparing')
        proc = subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def monitor():
            while not finished.wait(.2):
                if CANCEL.is_set():
                    stop_process(proc)
                    return
        threading.Thread(target=monitor,daemon=True).start()
        recent = []
        output = ''
        for line in proc.stdout:
            line = line.strip()
            recent.append(line)
            recent = recent[-8:]
            if line.startswith('FILE:'):
                output = line[5:]
            elif line.startswith('PROGRESS:'):
                fields = line[len('PROGRESS:'):].split('|')
                match = re.search(r'(\d+(?:\.\d+)?)%',fields[0])
                if match:
                    percent = min(100,max(0,float(match.group(1))))
                    details = [f'กำลังดาวน์โหลด {percent:.1f}%']
                    if len(fields)>1 and fields[1].strip() not in ('','NA','Unknown'):
                        details.append(fields[1].strip())
                    if len(fields)>2 and fields[2].strip() not in ('','NA','Unknown'):
                        details.append('เหลือประมาณ '+fields[2].strip())
                    send('progress',' · '.join(details),percent=percent,stage='downloading')
                else:
                    send('progress','กำลังดาวน์โหลด… รอข้อมูลขนาดไฟล์',stage='downloading')
            elif line.startswith(('POSTPROCESS:','[ExtractAudio]','[Merger]')):
                send('progress','กำลังแปลงเสียงหรือรวมไฟล์… กรุณารอสักครู่',stage='processing')
        code = proc.wait()
        if CANCEL.is_set():
            send('cancelled','ยกเลิกแล้ว (ไฟล์ชั่วคราวอาจยังอยู่ในโฟลเดอร์ดาวน์โหลด)')
        elif code:
            send('error','ดาวน์โหลดไม่สำเร็จ: '+' | '.join(recent)[-2500:])
        else:
            send('done','บันทึกแล้ว: '+(output or str(Path.home()/'Downloads'/'YouTube Personal')))
    except Exception as exc:
        send('error',str(exc))
    finally:
        finished.set()
        if proc and proc.poll() is None:
            stop_process(proc)

def read_exact(count):
    data = b''
    while len(data) < count:
        chunk = sys.stdin.buffer.read(count-len(data))
        if not chunk:
            raise EOFError
        data += chunk
    return data

def main():
    if os.name == 'nt':
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(),os.O_BINARY)
    worker = None
    try:
        while True:
            size = struct.unpack('<I',read_exact(4))[0]
            if not 0 < size <= 65536:
                raise ValueError('Invalid message size')
            request = json.loads(read_exact(size))
            if not isinstance(request,dict):
                raise ValueError('Invalid request')
            if request.get('action') == 'cancel':
                CANCEL.set()
            elif request.get('action') == 'check_update':
                if worker and worker.is_alive():
                    send('update_result','กำลังดาวน์โหลดอยู่ จะตรวจอัปเดตภายหลัง',updated=False)
                    continue
                try:
                    from github_update import check_update
                    result = check_update()
                    send('update_result',result['message'],updated=result['updated'])
                except Exception as exc:
                    send('update_result',str(exc),updated=False,error=True)
            elif request.get('action') == 'start':
                if worker and worker.is_alive():
                    continue
                CANCEL.clear()
                worker = threading.Thread(target=download,args=(request,))
                worker.start()
    except EOFError:
        pass
    except Exception as exc:
        send('error',str(exc))
    finally:
        CANCEL.set()
        if worker:
            worker.join()

if __name__ == '__main__':
    main()
