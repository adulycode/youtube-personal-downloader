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

def target_folder(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return Path.home() / 'Downloads' / 'YouTube Personal'
    if not isinstance(value, str) or len(value) > 500 or '\x00' in value:
        raise ValueError('โฟลเดอร์ที่บันทึกไม่ถูกต้อง')
    path = Path(value.strip()).expanduser()
    if not path.is_absolute():
        raise ValueError('กรุณาระบุพาธเต็มของโฟลเดอร์ เช่น D:\\YouTube')
    return path

def pick_folder(initial=None):
    if os.name != 'nt':
        return None
    import ctypes
    from ctypes import wintypes, byref, POINTER, c_void_p, c_uint, c_wchar_p, HRESULT
    ole32 = ctypes.windll.ole32
    shell32 = ctypes.windll.shell32
    ole32.CoInitialize(None)
    class GUID(ctypes.Structure):
        _fields_ = [('d1', c_uint), ('d2', wintypes.WORD), ('d3', wintypes.WORD), ('d4', ctypes.c_ubyte * 8)]
        def __init__(self, s):
            ole32.CLSIDFromString(c_wchar_p(s), byref(self))
    clsid = GUID('{DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}')
    iid_dlg = GUID('{D57C7288-D4AD-4768-BE02-9D969532D960}')
    iid_item = GUID('{43826D1E-E718-42EE-BC55-A1E261C37BFE}')
    dlg = c_void_p()
    if ole32.CoCreateInstance(byref(clsid), None, 1, byref(iid_dlg), byref(dlg)) != 0 or not dlg:
        return None
    vt = ctypes.cast(ctypes.cast(dlg, POINTER(c_void_p))[0], POINTER(c_void_p))
    Release = ctypes.WINFUNCTYPE(c_uint, c_void_p)(vt[2])
    Show = ctypes.WINFUNCTYPE(HRESULT, c_void_p, wintypes.HWND)(vt[3])
    SetOptions = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_uint)(vt[9])
    GetOptions = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_uint))(vt[10])
    SetFolder = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p)(vt[12])
    SetTitle = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_wchar_p)(vt[17])
    GetResult = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_void_p))(vt[20])
    try:
        opts = c_uint()
        GetOptions(dlg, byref(opts))
        SetOptions(dlg, opts.value | 0x20 | 0x40)
        SetTitle(dlg, 'เลือกโฟลเดอร์สำหรับบันทึกวิดีโอ / เสียง YouTube')
        start = Path.home() / 'Downloads'
        try:
            cand = target_folder(initial)
            start = cand if cand.is_dir() else (cand.parent if cand.parent.is_dir() else start)
        except Exception:
            pass
        item = c_void_p()
        if shell32.SHCreateItemFromParsingName(c_wchar_p(str(start)), None, byref(iid_item), byref(item)) == 0 and item:
            SetFolder(dlg, item)
            ivt0 = ctypes.cast(ctypes.cast(item, POINTER(c_void_p))[0], POINTER(c_void_p))
            ctypes.WINFUNCTYPE(c_uint, c_void_p)(ivt0[2])(item)
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if Show(dlg, hwnd) != 0:
            return None
        res = c_void_p()
        if GetResult(dlg, byref(res)) != 0 or not res:
            return None
        ivt = ctypes.cast(ctypes.cast(res, POINTER(c_void_p))[0], POINTER(c_void_p))
        GetDisplayName = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_uint, POINTER(c_void_p))(ivt[5])
        ReleaseItem = ctypes.WINFUNCTYPE(c_uint, c_void_p)(ivt[2])
        psz = c_void_p()
        path = None
        if GetDisplayName(res, 0x80058000, byref(psz)) == 0 and psz:
            path = ctypes.wstring_at(psz)
            ole32.CoTaskMemFree(psz)
        ReleaseItem(res)
        return path
    finally:
        Release(dlg)

def build_command(request):
    url = canonical_url(request.get('url'))
    mode = request.get('format')
    if mode not in ('mp3','mp4'):
        raise ValueError('Invalid format')
    quality = request.get('quality',1080)
    if type(quality) is not int or quality not in (720,1080,2160):
        raise ValueError('Invalid quality')
    target = target_folder(request.get('folder'))
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
        if request.get('askFolder'):
            send('progress','กำลังรอเลือกโฟลเดอร์ที่บันทึก…',stage='preparing')
            chosen = pick_folder(request.get('folder'))
            if not chosen:
                send('cancelled','ยกเลิกการเลือกโฟลเดอร์')
                return
            request = dict(request, folder=chosen)
            send('folder_selected',chosen,folder=chosen)
        target = target_folder(request.get('folder'))
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
            send('done','บันทึกแล้ว: '+(output or str(target)))
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
            elif request.get('action') == 'pick_folder':
                chosen = pick_folder(request.get('folder'))
                send('folder_result',chosen or '',folder=chosen)
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
