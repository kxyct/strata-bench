# -*- coding: utf-8 -*-
# 借用 Strata 0.2.1 的自动调参 —— 点火脚本（老大 2026-10-21 拍板「只要调参」）
# 用法：python tune-fire.py            （助手后台跑；90 秒后才动引擎，给对话留收尾时间）
# 流程：延时 -> 停咱引擎(杀 D:\Strata 进程树，先父后子) -> tune auto(thorough) -> 无论结果都重启引擎等就绪 -> 汇报退出
import json, os, subprocess, sys, time, socket, urllib.request
import psutil

HERE = os.path.dirname(os.path.abspath(__file__))
PY   = r"E:\Strata-app\control\python\python.exe"
STRATA = r"E:\Strata-app\control\strata.py"
TARGET = r"D:\Strata\Strata-main\strata-iq3_xxs.json"
START  = r"D:\Strata\Strata-main\START-HERE.bat"
OUT    = os.path.join(HERE, "tune-out.json")      # tune 的 json 报告
LOG    = os.path.join(HERE, "tune-run.log")       # 点火与 tune 全过程日志
STAT   = os.path.join(HERE, "tune-status.json")   # tune 的持久状态文件
MODE = "thorough"                                   # quick(约20分钟) 或 thorough(<=2h)；命令行第2参数可改
TIME_CAP_MIN = 210                                  # tune 时间上限（thorough 官方标称 <=2h，留 30min 余量）
KILL_CAP_S   = 60
READY_CAP_S  = 900

def log(msg):
    line = time.strftime("[%H:%M:%S] ") + str(msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def is_ours(p):
    """引擎栈成员 = exe 在 D:\\Strata 下，或 cmdline 是 serve.server 看护（它可能跑在系统 python 上，exe 不在 D 盘）。"""
    try:
        if (p.info.get("exe") or "").lower().startswith("d:\\strata"):
            return True
        cmd = " ".join(p.info.get("cmdline") or []).lower()
        return "serve.server" in cmd and "--engine" in cmd and "strata" in cmd
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return False

def engine_kill_tree():
    """杀掉所有 exe 在 D:\\Strata 下的进程（咱整套引擎栈），先父后子，避免看护进程重启。"""
    procs = [p for p in psutil.process_iter(["pid", "name", "exe", "cmdline"]) if is_ours(p)]
    if not procs:
        return 0
    byid = {p.pid: p for p in procs}
    ordered, done = [], set()
    while len(done) < len(procs):
        progress = False
        for p in procs:
            if p.pid in done:
                continue
            anc, pa, safe = [], p.pid, 0
            blocked = False
            while pa in byid and pa not in done and safe < 20:
                anc.append(pa)
                try:
                    pa = psutil.Process(pa).ppid()
                except psutil.NoSuchProcess:
                    blocked = True
                    break
                safe += 1
            if blocked or any(a not in done for a in anc):
                continue
            for a in reversed(anc):
                if a not in done:
                    ordered.append(a); done.add(a)
            ordered.append(p.pid); done.add(p.pid)
            progress = True
        if not progress:
            for p in procs:
                if p.pid not in done:
                    ordered.append(p.pid); done.add(p.pid)
    n = 0
    for pid in ordered:
        try:
            psutil.Process(pid).kill(); n += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return n

def wait_engine_gone(cap):
    t0 = time.time()
    while time.time() - t0 < cap:
        alive = sum(1 for p in psutil.process_iter(["pid", "name", "exe", "cmdline"]) if is_ours(p))
        if alive == 0:
            return True
        log(f"等引擎进程退出，还有 {alive} 个"); time.sleep(3)
    return False

def engine_up():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/metrics", timeout=5) as r:
            json.loads(r.read().decode("utf-8"))
        return True
    except Exception:
        return False

def restart_engine():
    if engine_up():
        log("8080 已有引擎在跑（tune 可能留了带参实例）")
    engine_kill_tree()   # 无条件清场：连临时端口上的遗留测量实例一起收，免得抢显存
    wait_engine_gone(KILL_CAP_S)
    flags = 0x00000008 | 0x00000200        # DETACHED | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(f'cmd /c ""{START}"', shell=True, creationflags=flags,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < READY_CAP_S:
        if engine_up():
            time.sleep(8)                  # metrics 通了再稳一稳
            if engine_up():
                return True
        time.sleep(10)
    return False

def main():
    global MODE
    delay = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    if len(sys.argv) > 2:
        MODE = sys.argv[2]
    log(f"点火计划：{delay}s 后停引擎 -> tune auto --mode {MODE} --goal speed -> 目标 {TARGET}")
    time.sleep(delay)

    n = engine_kill_tree()
    log(f"已发起杀除 {n} 个 D:\\Strata 进程")
    if not wait_engine_gone(KILL_CAP_S):
        log("引擎没停利索，不冒险测速，直接退出（引擎状态未定，稍后人工确认）")
        return 3
    s = socket.socket(); s.bind(("127.0.0.1", 8080)); s.close()
    log("8080 端口已释放，开始调参（thorough，可能 1~2 小时，期间助手不占引擎）")

    t_start = time.time()
    with open(LOG, "a", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            [PY, STRATA, "tune", "auto", "--mode", MODE, "--goal", "speed",
             "--name", "tune1021b",                       # 第二轮换名：tune1021 已被第一轮占用
             "--allow-small-differences",                 # 老大不在场，按交接推荐 B：放行 4 个「可能微小改变回答」的候选（adapt_async 仍不测）
             "--serve-dir", r"D:\Strata\Strata-main",
             "--status-file", STAT, "--output", "json", TARGET],
            stdout=lf, stderr=subprocess.STDOUT, cwd=r"E:\Strata-app\control")
    rc = None
    while time.time() - t_start < TIME_CAP_MIN * 60:
        rc = proc.poll()
        if rc is not None:
            break
        try:
            with open(STAT, encoding="utf-8") as f:
                st = json.load(f)
            log("tune 进行中: " + json.dumps(st, ensure_ascii=False)[:180])
        except Exception:
            pass
        time.sleep(45)
    if rc is None:
        log(f"超过 {TIME_CAP_MIN} 分钟上限，杀调参进程收尾")
        try:
            psutil.Process(proc.pid).kill()
        except Exception:
            pass
        rc = -9
    log(f"tune 结束 rc={rc}，用时 {(time.time()-t_start)/60:.1f} 分钟")

    ok = restart_engine()
    log(f"引擎恢复{'就绪' if ok else 'FAILED-未就绪'}；产物 tune-out.json / tune-run.log 在本目录")
    return 0 if ok else 4

if __name__ == "__main__":
    sys.exit(main())
