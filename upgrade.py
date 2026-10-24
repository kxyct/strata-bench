# 自动升级：停引擎 -> 备份已在旧目录 -> 替换 engine 二进制为 0.1.44.1 -> 重启 -> 验证
# 只换 engine\ 里的二进制；配置、中文补丁、模型文件全部不动。
import json
import os
import shutil
import subprocess
import time
import urllib.request

ENGINE_DIR = r'D:\Strata\Strata-main\engine'
NEW_DIR = r'E:\Strata-bench\new'
BACKUP = r'E:\Strata-bench\old_engine_backup'
VENV_PY = r'D:\Strata\Strata-main\.venv\Scripts\python.exe'
SERVER = r'D:\Strata\Strata-main\serve\server.py'
CFG = r'D:\Strata\Strata-main\strata-iq3_xxs.json'
LOG = r'E:\Strata-bench\upgrade.log'
SERVER_LOG = r'E:\Strata-bench\server_after_upgrade.log'

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + msg + '\n')

def kill_port(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=20).stdout
    for ln in out.splitlines():
        if (':%d ' % port) in ln and 'LISTENING' in ln:
            subprocess.run(['taskkill', '/F', '/PID', ln.split()[-1]], capture_output=True, timeout=20)

def main():
    log('=== upgrade start ===')
    time.sleep(25)  # 给助手时间把消息发完
    log('step1: stop engine')
    kill_port(8080)
    for im in ('strata.exe', 'strata-vision.exe'):
        subprocess.run(['taskkill', '/F', '/IM', im], capture_output=True, timeout=20)
    time.sleep(5)

    log('step2: replace engine binaries (backup at %s)' % BACKUP)
    for name in ('strata.exe', 'strata-vision.exe', 'strata_kq.dll', 'BUILD.json'):
        shutil.copy2(os.path.join(NEW_DIR, name), os.path.join(ENGINE_DIR, name))
        log('copied ' + name)
    ver = json.load(open(os.path.join(ENGINE_DIR, 'BUILD.json'), encoding='utf-8'))['version']
    log('engine BUILD.json version now: %s' % ver)

    # 新位置第一次执行可能被杀软拦（上次 WinError 5 就是这么来的）→ 先手动跑一次放行
    try:
        subprocess.run([os.path.join(ENGINE_DIR, 'strata.exe'), '--version'],
                       capture_output=True, timeout=60)
        log('warm-run engine exe ok')
    except Exception as e:
        log('warm-run failed: %r' % e)

    log('step3: restart server on 8080')
    subprocess.Popen([VENV_PY, SERVER, '--engine', 'strata', '--config', CFG, '--port', '8080'],
                     cwd=r'D:\Strata\Strata-main',
                     stdout=open(SERVER_LOG, 'a'), stderr=subprocess.STDOUT)
    ok = False
    t0 = time.time()
    while time.time() - t0 < 420:
        try:
            with urllib.request.urlopen('http://127.0.0.1:8080/v1/models', timeout=5) as r:
                if r.status == 200:
                    ok = True
                    break
        except Exception:
            pass
        time.sleep(3)
    log('server ready: %s after %ds' % (ok, int(time.time() - t0)))

    # 验证：发一个最小请求，确认新引擎真的在答题
    try:
        body = json.dumps({'model': 'qwen3.8-flash-next-iq3_xxs', 'max_tokens': 8,
                           'messages': [{'role': 'user', 'content': '说一个字'}]}).encode()
        req = urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions', data=body,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=180) as r:
            payload = json.loads(r.read())
        log('smoke test ok: %s' % json.dumps(payload.get('choices', [{}])[0].get('message', {}).get('content', ''))[:80])
    except Exception as e:
        log('smoke test FAILED: %r' % e)
        ok = False

    with open(r'E:\Strata-bench\UPGRADE_RESULT.txt', 'w', encoding='utf-8') as f:
        f.write('升级结果（2026-10-16）\n==================\n')
        f.write('引擎版本: 0.1.41 -> %s\n' % ver)
        f.write('服务恢复(8080): %s\n' % ('成功' if ok else '失败，见 upgrade.log'))
        f.write('只替换了 engine\\ 下 4 个文件；配置/中文补丁/模型未动。\n')
        f.write('回退方法：把 E:\\Strata-bench\\old_engine_backup\\ 里的 3 个文件复制回 D:\\Strata\\Strata-main\\engine\\ 覆盖，再重启引擎。\n')
    log('=== upgrade done ===')

if __name__ == '__main__':
    main()
