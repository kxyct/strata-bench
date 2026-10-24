# 自动基准：停旧引擎 -> 起新引擎(0.1.44.1, 8081) -> 测速 -> 换回旧引擎(8080)
# 全程自动，中途旧引擎(助手本人)会下线几分钟，结束后自动恢复。
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = r'E:\Strata-bench'
VENV_PY = r'D:\Strata\Strata-main\.venv\Scripts\python.exe'
SERVER = r'D:\Strata\Strata-main\serve\server.py'
OLD_CFG = r'D:\Strata\Strata-main\strata-iq3_xxs.json'
NEW_CFG = os.path.join(HERE, 'iq3_xxs_new.json')
NEW_LOG = os.path.join(HERE, 'new.log')
NEW_SERVER_LOG = os.path.join(HERE, 'new_server.log')
BENCH_LOG = os.path.join(HERE, 'bench_new.log')

def log(msg):
    line = time.strftime('%H:%M:%S ') + msg
    with open(BENCH_LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def kill_port(port):
    try:
        out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=20).stdout
        for ln in out.splitlines():
            if (':%d ' % port) in ln and 'LISTENING' in ln:
                pid = ln.split()[-1]
                subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, timeout=20)
                log('killed listener pid %s on %d' % (pid, port))
    except Exception as e:
        log('kill_port %d error: %r' % (port, e))

def kill_engines():
    for im in ('strata.exe', 'strata-vision.exe'):
        subprocess.run(['taskkill', '/F', '/IM', im], capture_output=True, timeout=20)

def start_server(cfg, port, server_log):
    p = subprocess.Popen(
        [VENV_PY, SERVER, '--engine', 'strata', '--config', cfg, '--port', str(port)],
        cwd=r'D:\Strata\Strata-main',
        stdout=open(server_log, 'a'), stderr=subprocess.STDOUT)
    log('server started pid %s cfg %s port %d' % (p.pid, cfg, port))
    return p

def wait_ready(port, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d/v1/models' % port, timeout=5) as r:
                if r.status == 200:
                    log('port %d ready after %ds' % (port, int(time.time() - t0)))
                    return True
        except Exception:
            pass
        time.sleep(3)
    log('port %d NOT ready after %ds' % (port, timeout))
    return False

def run_bench(port, out):
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, 'measure_parallel.py'),
         '--host', 'http://127.0.0.1:%d' % port, '--tier', '4k', '--tokens', '4096',
         '--concurrent', '1', '--runs', '3', '--log', NEW_LOG, '--out', out],
        capture_output=True, text=True, timeout=500, cwd=HERE)
    log('bench rc=%s' % r.returncode)
    for ln in (r.stdout or '').splitlines()[-6:]:
        log('bench: ' + ln)
    return r.returncode == 0

def main():
    log('=== bench_new start ===')
    time.sleep(25)  # 给助手时间把消息发完
    log('step1: stop old engine')
    kill_port(8080)
    kill_engines()
    time.sleep(3)

    log('step2: start new engine 0.1.44.1 on 8081')
    open(NEW_LOG, 'a').close()
    open(NEW_SERVER_LOG, 'w').close()
    start_server(NEW_CFG, 8081, NEW_SERVER_LOG)
    if not wait_ready(8081, 420):
        log('new engine failed to start; server log tail:')
        try:
            with open(NEW_SERVER_LOG, encoding='utf-8', errors='replace') as f:
                for ln in f.read().splitlines()[-15:]:
                    log('srvlog: ' + ln)
        except Exception as e:
            log('read srvlog failed: %r' % e)
    else:
        log('step3: bench new engine')
        run_bench(8081, os.path.join(HERE, 'new-4k.json'))

    log('step4: stop new engine')
    kill_port(8081)
    kill_engines()
    time.sleep(3)

    log('step5: restart old engine on 8080')
    start_server(OLD_CFG, 8080, os.path.join(HERE, 'old_server_restart.log'))
    wait_ready(8080, 420)
    log('=== bench_new done ===')

if __name__ == '__main__':
    main()
