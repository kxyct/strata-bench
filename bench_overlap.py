# A/B：STRATA_ADAPT_OVERLAP=1 vs 默认关（基线 = new-4k.json：decode 82.4 / prefill 922.8 / e2e 33.4 / hit 66.2）
# 流程：停引擎 -> 带 overlap=1 起 8081 -> 测 -> 停 -> 恢复默认 8080 -> 验证
import json, os, subprocess, time, urllib.request

HERE = r'E:\Strata-bench'
VENV_PY = r'D:\Strata\Strata-main\.venv\Scripts\python.exe'
SERVER = r'D:\Strata\Strata-main\serve\server.py'
MAIN_CFG = r'D:\Strata\Strata-main\strata-iq3_xxs.json'
OVL_CFG = os.path.join(HERE, 'iq3_xxs_overlap.json')
NEW_LOG = os.path.join(HERE, 'new.log')
LOG = os.path.join(HERE, 'bench_overlap.log')

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

def main():
    log('=== overlap A/B start ===')
    time.sleep(25)
    log('stop engine')
    kill_port(8080); kill_engines(); time.sleep(5)
    log('start with STRATA_ADAPT_OVERLAP=1 on 8081')
    open(NEW_LOG, 'a').close()
    start(OVL_CFG, 8081, os.path.join(HERE, 'overlap_server.log'))
    if not wait_ready(8081, 420):
        log('overlap engine NOT ready; abort to default')
    else:
        # 确认开关真的生效：引擎日志会写明 overlap 开/关
        time.sleep(2)
        with open(NEW_LOG, encoding='utf-8', errors='replace') as f:
            txt = f.read()
        hit = [ln for ln in txt.splitlines() if 'overlap' in ln.lower()]
        log('overlap log lines: %s' % (hit[-3:] if hit else 'NONE FOUND'))
        r = subprocess.run([os.sys.executable, os.path.join(HERE, 'measure_parallel.py'),
                            '--host', 'http://127.0.0.1:8081', '--tier', '4k-overlap', '--tokens', '4096',
                            '--concurrent', '1', '--runs', '3', '--log', NEW_LOG,
                            '--out', os.path.join(HERE, 'new-4k-overlap.json')],
                           capture_output=True, text=True, timeout=500, cwd=HERE)
        for ln in (r.stdout or '').splitlines()[-6:]:
            log('bench: ' + ln)
    log('stop overlap engine')
    kill_port(8081); kill_engines(); time.sleep(5)
    log('restore default engine on 8080')
    start(MAIN_CFG, 8080, os.path.join(HERE, 'server_after_overlap.log'))
    ok = wait_ready(8080, 420)
    log('default engine ready: %s' % ok)
    log('=== overlap A/B done ===')

if __name__ == '__main__':
    main()
