# A/B：--prefill auto vs auto:32768（大提示词提速），四段交替重启 A1→B1→A2→B2
# 规格 = prefill-ab-spec.md；骨架照抄 bench_overlap.py（10-16 实测过的起停/测量路子）。
# 跑法：老大双击 对比大提示词提速.bat（中途 8080 引擎是停的，最后一段自动恢复 8080）。
import hashlib, json, os, re, subprocess, threading, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = r'D:\Strata\Strata-main\.venv\Scripts\python.exe'
SERVER = r'D:\Strata\Strata-main\serve\server.py'
MAIN_CFG = r'D:\Strata\Strata-main\strata-iq3_xxs.json'
B_CFG = os.path.join(HERE, 'prefill-ab-b.json')
MAIN_LOG = r'D:\Strata\Strata-main\strata-iq3_xxs.log'
B_LOG = os.path.join(HERE, 'prefill_b.log')
LOG = os.path.join(HERE, 'bench_prefill.log')
MODEL = 'qwen3.8-flash-next-iq3_xxs'
NONCE4 = '77001'  # 四段用同一个 nonce → 4K 提示词逐字相同，答案可比（必须字符串：measure_parallel 里 nonce+"\n" 直接拼接）

PROMPT_RE = re.compile(
    r'prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\), '
    r'(\d+) generated in (\d+) ms \(([\d.]+) tok/s\)')
CHUNK_RE = re.compile(r'prompt chunk auto: (\d+) tokens')
WARN_RE = re.compile(r'WARNING|LOW:|commit limit|FAILED|stall', re.I)

_lock = threading.Lock()


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


def start(cfg, port):
    subprocess.Popen([VENV_PY, SERVER, '--engine', 'strata', '--config', cfg, '--port', str(port)],
                     cwd=r'D:\Strata\Strata-main')


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


def read_after(path, offset):
    """读日志从 offset 起新增的行。"""
    try:
        with open(path, 'rb') as f:
            f.seek(offset)
            return f.read().decode('utf-8', errors='replace').splitlines()
    except OSError:
        return []


def post_once(port, prompt, max_tokens=256):
    base = {'model': MODEL, 'max_tokens': max_tokens, 'stream': False,
            'messages': [{'role': 'user', 'content': prompt}]}

    def send(body_dict):
        req = urllib.request.Request('http://127.0.0.1:%d/v1/chat/completions' % port,
                                     data=json.dumps(body_dict).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=1800) as r:
            return json.loads(r.read().decode('utf-8'))

    try:
        payload = send(dict(base, temperature=0.0))  # 贪心，四段答案才可比
    except Exception:
        log('4K 请求带 temperature 失败，退回服务端默认参数重试')
        payload = send(base)
    msg = payload['choices'][0]['message']
    return ((msg.get('reasoning_content') or '') + '||' + (msg.get('content') or '')), payload.get('usage', {})


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def run_arm(name, cfg, eng_log):
    log('=== %s: start (cfg=%s port=8081) ===' % (name, os.path.basename(cfg)))
    kill_port(8081); kill_engines(); time.sleep(4)
    open(eng_log, 'a').close()
    off = os.path.getsize(eng_log)
    start(cfg, 8081)
    if not wait_ready(8081, 420):
        log('%s START FAILED (没起来或自杀) — 记失败继续下一段' % name)
        kill_port(8081); kill_engines()
        return {'name': name, 'ok': False}
    time.sleep(2)
    new = read_after(eng_log, off)
    chunks = CHUNK_RE.findall('\n'.join(new))
    chunk = int(chunks[-1]) if chunks else None
    log('%s chunk auto 生效值 = %s tokens' % (name, chunk))

    # 4K 逐字对照（兼当热身，本机每批首轮偏热）
    import measure_parallel as mp
    p4 = mp.build_prompt(NONCE4, 4096)
    ans4, u4 = post_once(8081, p4)
    sha4 = hashlib.sha1(ans4.encode('utf-8')).hexdigest()[:12]
    log('%s 4K: prompt_tokens=%s 答案sha1=%s' % (name, u4.get('prompt_tokens'), sha4))

    # 36K 三轮，弃首轮，后两轮 prefill 取中位
    subprocess.run([os.sys.executable, os.path.join(HERE, 'measure_parallel.py'),
                    '--host', 'http://127.0.0.1:8081', '--tier', '36k-' + name, '--tokens', '36864',
                    '--concurrent', '1', '--runs', '3', '--log', eng_log,
                    '--out', os.path.join(HERE, 'prefab-%s-36k.json' % name)],
                   capture_output=True, timeout=2000, cwd=HERE)
    new = read_after(eng_log, off)
    rows = [m for m in PROMPT_RE.finditer('\n'.join(new))
            if int(m.group(1)) >= 32768]
    pre = [float(m.group(6)) for m in rows]
    ptoks = [int(m.group(1)) for m in rows]
    if len(pre) >= 2:
        pre2 = pre[1:]
        pre_med = med(pre2)
    else:
        pre2 = pre
        pre_med = med(pre)
    warns = [ln for ln in new if WARN_RE.search(ln)][-6:]
    log('%s 36K prompt_tokens=%s 每次prefill=%s 后两次中位=%s' % (name, ptoks, pre[1:] or pre, pre_med))
    for w in warns:
        log('%s 警告行: %s' % (name, w[:180]))
    kill_port(8081); kill_engines(); time.sleep(4)
    return {'name': name, 'ok': True, 'chunk': chunk, 'sha4': sha4,
            'ptoks': ptoks, 'pre_all': pre, 'pre_med': pre_med,
            'warns': warns}


def main():
    log('=== prefill A/B start (A1 B1 A2 B2, 36864 tokens) ===')
    kill_port(8080); kill_engines(); time.sleep(5)
    results = []
    for name, cfg, eng in [('A1', MAIN_CFG, MAIN_LOG), ('B1', B_CFG, B_LOG),
                           ('A2', MAIN_CFG, MAIN_LOG), ('B2', B_CFG, B_LOG)]:
        try:
            results.append(run_arm(name, cfg, eng))
        except Exception as e:
            log('%s EXCEPTION: %r — 继续下一段' % (name, e))
            kill_port(8081); kill_engines()
            results.append({'name': name, 'ok': False})

    R = {r['name']: r for r in results}

    def gv(n, k):
        return R.get(n, {}).get(k)

    a1, a2, b1, b2 = gv('A1', 'pre_med'), gv('A2', 'pre_med'), gv('B1', 'pre_med'), gv('B2', 'pre_med')
    shas = {n: gv(n, 'sha4') for n in ('A1', 'A2', 'B1', 'B2')}
    chks = {n: gv(n, 'chunk') for n in ('A1', 'A2', 'B1', 'B2')}
    grew = all(chks.get(n) for n in ('B1', 'B2')) and all(chks.get(n) for n in ('A1', 'A2')) \
        and min(chks['B1'], chks['B2']) > max(chks['A1'], chks['A2'])
    if None in (a1, a2, b1, b2):
        verdict = '数据不全（有段失败）— 看失败段的记录定性下结论'
    else:
        drift = max(abs(a1 - a2), abs(b1 - b2))
        e1, e2 = b1 - a1, b2 - a2
        if not grew:
            verdict = 'B 组 chunk 没有变大 → 开关空转（引擎不肯借缓冲），结案'
        elif e1 > 0 and e2 > 0 and min(e1, e2) > drift:
            verdict = 'B 赢：两次同向更快且增益超过漂移 (e1=+%.1f e2=+%.1f drift=%.1f) → 待老大点头转正' % (e1, e2, drift)
        else:
            verdict = 'B 不赢：方向不稳或增益没超过漂移 (e1=%+.1f e2=%+.1f drift=%.1f) → 维持 auto' % (e1, e2, drift)
    summary = {'results': results, 'verdict': verdict, '4k_sha1': shas, 'chunk': chks}
    with open(os.path.join(HERE, 'prefab-summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    log('=== 判定：%s ===' % verdict)
    log('4K答案sha1: %s' % shas)
    log('chunk生效: %s' % chks)
    log('恢复 8080 日常引擎')
    start(MAIN_CFG, 8080)
    log('8080 就绪: %s — 助手应能醒来说话' % wait_ready(8080, 420))
    log('=== prefill A/B done ===')


if __name__ == '__main__':
    main()
