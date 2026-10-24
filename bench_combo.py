# 组合测试：overlap-only（基线）vs overlap+unbuffered，4k 和 16k 两档
# 一个周期内两次起 8081，最后恢复 8080 正式配置（overlap-only）
import json, os, subprocess, time, urllib.request

HERE = r'E:\Strata-bench'
VENV_PY = r'D:\Strata\Strata-main\.venv\Scripts\python.exe'
SERVER = r'D:\Strata\Strata-main\serve\server.py'
MAIN_CFG = r'D:\Strata\Strata-main\strata-iq3_xxs.json'
LOG = os.path.join(HERE, 'bench_combo.log')
NEW_LOG = os.path.join(HERE, 'new.log')

def log(m):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + m + '\n')

def kill_port(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=20).stdout
    for ln in out.splitlines():
        if (':%d ' % port) in ln and 'LISTENING' in ln:
            subprocess.run(['taskkill', '/F', '/PID', ln.split()[-1]], capture_output=True, timeout=20)

def kill_engines():
    for im in ('strata.exe', 'strata-vision.exe'):
        subprocess.run(['taskkill', '/F', '/IM', im], capture_output=True, timeout=20)

def start(cfg, port, slog):
    subprocess.Popen([VENV_PY, SERVER, '--engine', 'strata', '--config', cfg, '--port', str(port)],
                     cwd=r'D:\Strata\Strata-main', stdout=open(slog, 'a'), stderr=subprocess.STDOUT)

def wait_ready(port, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d/v1/models' % port, timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False

def bench(tokens, runs, out):
    r = subprocess.run([os.sys.executable, os.path.join(HERE, 'measure_parallel.py'),
                        '--host', 'http://127.0.0.1:8081', '--tier', out.replace('.json', ''),
                        '--tokens', str(tokens), '--concurrent', '1', '--runs', str(runs),
                        '--log', NEW_LOG, '--out', os.path.join(HERE, out)],
                       capture_output=True, text=True, timeout=500, cwd=HERE)
    for ln in (r.stdout or '').splitlines()[-2:]:
        log('bench %s: %s' % (out, ln))

def main():
    log('=== combo A/B start ===')
    time.sleep(25)
    kill_port(8080); kill_engines(); time.sleep(5)

    log('phase1: overlap-only baseline 16k')
    open(NEW_LOG, 'a').close()
    start(os.path.join(HERE, 'iq3_xxs_overlap.json'), 8081, os.path.join(HERE, 'combo1_server.log'))
    if wait_ready(8081, 420):
        bench(16384, 2, 'base16-overlap.json')
    kill_port(8081); kill_engines(); time.sleep(5)

    log('phase2: overlap+unbuffered 4k + 16k')
    start(os.path.join(HERE, 'iq3_xxs_combo.json'), 8081, os.path.join(HERE, 'combo2_server.log'))
    if wait_ready(8081, 420):
        bench(4096, 2, 'combo-4k.json')
        bench(16384, 2, 'combo-16k.json')
    kill_port(8081); kill_engines(); time.sleep(5)

    log('phase3: restore main config (overlap-only) on 8080')
    start(MAIN_CFG, 8080, os.path.join(HERE, 'server_after_combo.log'))
    log('8080 ready: %s' % wait_ready(8080, 420))
    log('=== combo A/B done ===')

if __name__ == '__main__':
    main()
