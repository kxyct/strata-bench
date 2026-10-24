# 用计划任务起引擎（新 token 可能带上新授予的大页权限）-> 查 arena -> 基准
import subprocess, time, urllib.request, os

HERE = r'E:\Strata-bench'
LOG = os.path.join(HERE, 'lp_task.log')
ENG_LOG = r'D:\Strata\Strata-main\strata-iq3_xxs.log'
BAT = os.path.join(HERE, 'start_via_task.bat')
TASK = 'StrataLpTest'

def log(m):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + m + '\n')

def kill_port(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=20).stdout
    for ln in out.splitlines():
        if (':%d ' % port) in ln and 'LISTENING' in ln:
            subprocess.run(['taskkill', '/F', '/PID', ln.split()[-1]], capture_output=True, timeout=20)

def main():
    log('=== lp task test start ===')
    time.sleep(25)
    # 启动 bat（纯 ASCII，内容不含中文）
    with open(BAT, 'w', encoding='ascii') as f:
        f.write('@echo off\r\ntitle Strata LP engine\r\ncd /d "D:\\Strata\\Strata-main"\r\n'
                '"D:\\Strata\\Strata-main\\.venv\\Scripts\\python.exe" "D:\\Strata\\Strata-main\\serve\\server.py" '
                '--engine strata --config "D:\\Strata\\Strata-main\\strata-iq3_xxs.json" --port 8080\r\n')
    kill_port(8080)
    for im in ('strata.exe', 'strata-vision.exe'):
        subprocess.run(['taskkill', '/F', '/IM', im], capture_output=True, timeout=20)
    time.sleep(5)

    st = time.strftime('%H:%M', time.localtime(time.time() + 90))
    r1 = subprocess.run(['schtasks', '/create', '/tn', TASK, '/tr', BAT, '/sc', 'once', '/st', st, '/f'],
                        capture_output=True, text=True, timeout=30)
    log('create rc=%s %s' % (r1.returncode, (r1.stdout or r1.stderr or '').strip()[:120]))
    r2 = subprocess.run(['schtasks', '/run', '/tn', TASK], capture_output=True, text=True, timeout=30)
    log('run rc=%s %s' % (r2.returncode, (r2.stdout or r2.stderr or '').strip()[:120]))

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
    for ln in arena[-2:]:
        log('arena: ' + ln.strip())

    if ok:
        r = subprocess.run([os.sys.executable, os.path.join(HERE, 'measure_parallel.py'),
                            '--host', 'http://127.0.0.1:8080', '--tier', '4k-lp2', '--tokens', '4096',
                            '--concurrent', '1', '--runs', '3', '--log', ENG_LOG,
                            '--out', os.path.join(HERE, 'lp2-4k.json')],
                           capture_output=True, text=True, timeout=500, cwd=HERE)
        for ln in (r.stdout or '').splitlines()[-5:]:
            log('bench: ' + ln)
    subprocess.run(['schtasks', '/delete', '/tn', TASK, '/f'], capture_output=True, timeout=20)
    log('=== lp task test done ===')

if __name__ == '__main__':
    main()
