# 重启引擎（让大页权限进新进程）-> 查 arena 日志 -> 直接跑 4k 基准对比 86.0 基线
import os, subprocess, time, urllib.request

HERE = r'E:\Strata-bench'
LOG = os.path.join(HERE, 'restart_bench.log')
ENG_LOG = r'D:\Strata\Strata-main\strata-iq3_xxs.log'

def log(m):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + m + '\n')

def kill_port(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=20).stdout
    for ln in out.splitlines():
        if (':%d ' % port) in ln and 'LISTENING' in ln:
            subprocess.run(['taskkill', '/F', '/PID', ln.split()[-1]], capture_output=True, timeout=20)

def main():
    log('=== restart+bench start ===')
    time.sleep(25)
    kill_port(8080)
    for im in ('strata.exe', 'strata-vision.exe'):
        subprocess.run(['taskkill', '/F', '/IM', im], capture_output=True, timeout=20)
    time.sleep(5)
    subprocess.Popen([r'D:\Strata\Strata-main\.venv\Scripts\python.exe',
                      r'D:\Strata\Strata-main\serve\server.py', '--engine', 'strata',
                      '--config', r'D:\Strata\Strata-main\strata-iq3_xxs.json', '--port', '8080'],
                     cwd=r'D:\Strata\Strata-main',
                     stdout=open(os.path.join(HERE, 'server_lp.log'), 'a'), stderr=subprocess.STDOUT)
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
    with open(ENG_LOG, encoding='utf-8', errors='replace') as f:
        arena = [ln for ln in f.read().splitlines() if 'arena' in ln]
    for ln in arena[-3:]:
        log('arena: ' + ln.strip())
    if ok:
        r = subprocess.run([os.sys.executable, os.path.join(HERE, 'measure_parallel.py'),
                            '--host', 'http://127.0.0.1:8080', '--tier', '4k-lp', '--tokens', '4096',
                            '--concurrent', '1', '--runs', '3', '--log', ENG_LOG,
                            '--out', os.path.join(HERE, 'largepage-4k.json')],
                           capture_output=True, text=True, timeout=500, cwd=HERE)
        for ln in (r.stdout or '').splitlines()[-5:]:
            log('bench: ' + ln)
    log('=== restart+bench done ===')

if __name__ == '__main__':
    main()
