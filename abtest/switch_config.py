# 切换引擎用哪个模型（改 D:\Strata\Strata-main\strata-iq3_xxs.json，改前自动备份）
# 用法： python switch_config.py --to sc117        切到无审核版
#        python switch_config.py --to official     切回现在的原版
#        python switch_config.py --show            只看当前配置指向哪份模型，不改任何东西
import argparse, json, os, shutil, sys, time

CFG = r'D:\Strata\Strata-main\strata-iq3_xxs.json'
OFF_NATIVE = r'D:\strata\Strata-data\models\IQ3_XXS\Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf'
OFF_PLE = r'D:\strata\Strata-data\models\IQ3_XXS\Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf'
OFF_PACK = r'D:\strata\Strata-data\packs\iq3_xxs'
SC117_DIR = r'D:\Strata\Strata-data\models\sc117_iq3_xxs'
SC_NATIVE = os.path.join(SC117_DIR, 'Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_XXS-00001-of-00002.gguf')
SC_PLE = os.path.join(SC117_DIR, 'Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_XXS-00002-of-00002.gguf')
SC_PACK = r'D:\strata\Strata-data\packs\sc117_iq3_xxs'
SC117_SHARD1_BYTES = 47342144896
SC117_SHARD2_BYTES = 28800138432

def load():
    with open(CFG, 'r', encoding='utf-8') as f:
        return json.load(f)

def get(cfg, flag):
    a = cfg['args']
    return a[a.index(flag) + 1] if flag in a else None

def setv(cfg, flag, val):
    a = cfg['args']
    a[a.index(flag) + 1] = val

def show(cfg):
    print('当前 --pack    :', get(cfg, '--pack'))
    print('当前 --native  :', get(cfg, '--native'))
    print('当前 --ple-gguf:', get(cfg, '--ple-gguf'))
    print('当前 tokenizer :', cfg.get('tokenizer'))
    print('当前 vision    :', cfg.get('vision', {}).get('model'))
    print('当前 --mtp     :', get(cfg, '--mtp'))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--to', choices=['sc117', 'official'])
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args()
    cfg = load()
    if a.show or not a.to:
        show(cfg)
        return
    if a.to == 'official':
        pack, native, ple = OFF_PACK, OFF_NATIVE, OFF_PLE
    else:
        pack, native, ple = SC_PACK, SC_NATIVE, SC_PLE
        # 切过去之前先确认东西真的齐了，否则引擎起不来更难查
        for p, want in ((native, SC117_SHARD1_BYTES), (ple, SC117_SHARD2_BYTES)):
            if not os.path.isfile(p):
                print('缺文件，不能切:', p); sys.exit(2)
            got = os.path.getsize(p)
            if got != want:
                print('文件没下完，不能切: %s  现有 %d / 应为 %d' % (p, got, want)); sys.exit(2)
        if not os.path.isdir(pack) or not os.path.isfile(os.path.join(pack, 'native_experts.txt')):
            print('pack 还没建，不能切。先跑 iq_pack.py:', pack); sys.exit(2)
        if not os.path.isdir(os.path.join(pack, 'tokenizer')):
            print('新 pack 里没有 tokenizer 目录，先让我看一下:', pack); sys.exit(2)
    bak = CFG + '.bak-' + a.to + '-' + time.strftime('%Y%m%d-%H%M%S')
    shutil.copy2(CFG, bak)
    before = (get(cfg, '--pack'), get(cfg, '--native'), get(cfg, '--ple-gguf'),
              cfg.get('tokenizer'), cfg.get('vision', {}).get('model'))
    setv(cfg, '--pack', pack)
    setv(cfg, '--native', native)
    setv(cfg, '--ple-gguf', ple)
    cfg['tokenizer'] = os.path.join(pack, 'tokenizer')
    if 'vision' in cfg:
        cfg['vision']['model'] = native
    with open(CFG, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    print('已备份原配置 ->', bak)
    print('切换前:', *before, sep='\n  ')
    print('切换后:\n  ', pack, '\n  ', native, '\n  ', ple, '\n  ', cfg.get('tokenizer'),
          '\n  ', cfg.get('vision', {}).get('model'))
    print('切换完成。要生效必须重启引擎（双击对应的 bat）。')

main()
