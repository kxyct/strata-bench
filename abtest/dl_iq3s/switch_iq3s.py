# -*- coding: utf-8 -*-
# IQ3_XXS -> IQ3_S 一次性切换脚本（改前自动备份配置；撤回 = 把备份覆盖回去再重启）
# 步骤：1) 分片硬链进 models\sc117_iq3_s\  2) iq_pack.py 建专家包  3) 改配置四处路径
import json, os, subprocess, sys

S = r"D:\Strata\Strata-main"
DATA = r"D:\Strata\Strata-data"
DL = r"E:\Desktop\aigz\strata-bench\abtest\dl_iq3s"
CFG = os.path.join(S, "strata-iq3_xxs.json")
SHA = "40f369eca301ec6ea318dbb671b3132c26a2f0b89aa5458a7051b33215ee296c"
S1_NAME = "Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00001-of-00002.gguf"
S2_NAME = "Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00002-of-00002.gguf"
OLD_S2 = os.path.join(DATA, "models", "sc117_iq3_xxs", "Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_XXS-00002-of-00002.gguf")
d1 = os.path.join(DATA, "models", "sc117_iq3_s")
s1 = os.path.join(d1, S1_NAME)
s2 = os.path.join(d1, S2_NAME)
PACK = os.path.join(DATA, "packs", "sc117_iq3_s")

def sha256(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def main():
    src1 = os.path.join(DL, S1_NAME)
    if not os.path.isfile(src1):
        print("源文件没下完，先不下链接：", src1); sys.exit(2)
    if os.path.getsize(src1) != 55063448064:
        print("下载尺寸不对：", os.path.getsize(src1)); sys.exit(2)
    os.makedirs(d1, exist_ok=True)
    if not os.path.exists(s2):
        os.link(OLD_S2, s2)   # 官方清单两处 shard2 指纹相同 -> 内容一致，硬链不占新空间
        print("shard2 硬链完成")
    if not os.path.exists(s1):
        d = sha256(src1)
        if d != SHA:
            print("sha256 校验不过：", d); sys.exit(2)
        import shutil
        shutil.move(src1, s1)   # 跨盘(E->D)不能硬链，物理搬移，E 盘腾出 51 GB
        print("shard1 校验通过，已物理搬移到 D 盘")
    if not os.path.isfile(os.path.join(PACK, "dense.bin")):
        cmd = [os.path.join(S, ".venv", "Scripts", "python.exe"),
               os.path.join(S, "tools", "iq_pack.py"),
               "--gguf", s1, "--out", PACK]
        print("打包中（读 77 GB，约几分钟）:", " ".join(cmd))
        subprocess.run(cmd, check=True, cwd=S)
    else:
        print("专家包已存在，跳过打包")
    cfg = json.load(open(CFG, encoding="utf-8"))
    args = cfg.get("args") or []
    def rep(flag, val):
        if flag in args:
            args[args.index(flag) + 1] = val
    rep("--native", s1)
    rep("--ple-gguf", s2)
    rep("--pack", PACK)
    cfg["tokenizer"] = os.path.join(PACK, "tokenizer")
    cfg["args"] = args
    json.dump(cfg, open(CFG, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("配置已切换。--native =", args[args.index("--native") + 1])
    print("--pack =", args[args.index("--pack") + 1], " tokenizer =", cfg["tokenizer"])
    print("IQ3S-SWITCH-OK")

main()
