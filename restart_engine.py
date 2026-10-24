# 重启正式引擎（让新写入的 env 生效）并验证 overlap 开启
import os, subprocess, time, urllib.request
LOG = r'E:\Strata-bench\restart.log'
def log(m):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + m + '\n')
def kill_port(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=20).stdout
    for ln in out.splitlines():
        if (':%d ' % port) in ln and 'LISTENING' in ln:
            subprocess.run(['taskkill', '/F', '/PID', ln.split()[-1]], capture_output=True, timeout=20)
def main():
    log('=== restart start ===')
    time.sleep(25)
    kill_port(8080)
    for im in ('strata.exe', 'strata-vision.exe'):
        subprocess.run(['taskkill', '/F', '/IM', im], capture_output=True, timeout=20)
    time.sleep(5)
    subprocess.Popen([r'D:\Strata\Strata-main\.venv\Scripts\python.exe',
                      r'D:\Strata\Strata-main\serve\server.py', '--engine', 'strata',
                      '--config', r'D:\Strata\Strata-main\strata-iq3_xxs.json', '--port', '8080'],
                     cwd=r'D:\Strata\Strata-main',
                     stdout=open(r'E:\Strata-bench\server_final.log', 'a'), stderr=subprocess.STDOUT)
    ok = False
    t0 = time.time()
    while time.time() - t0 < 420:
        try:
            with urllib.request.urlopen('http://127.0.0.1:8080/v1/models', timeout=5) as r:
                if r.status == 200:
                    ok = True; break
        except Exception:
            pass
        time.sleep(3)
    log('8080 ready: %s after %ds' % (ok, int(time.time() - t0)))
    try:
        with open(r'D:\Strata\Strata-main\strata-iq3_xxs.log', encoding='utf-8', errors='replace') as f:
            lines = [ln for ln in f.read().splitlines() if 'adaptive overlap' in ln.lower()]
        log('overlap lines (last 2): %s' % lines[-2:])
    except Exception as e:
        log('log check failed: %r' % e)
    log('=== restart done ===')
if __name__ == '__main__':
    main()
