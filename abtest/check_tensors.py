# 第一关：逐张量 blake2b 对比（验证下载的是不是真消融版、改动是不是只有 144 个）
#
# 用法：
#   python check_tensors.py --a 文件X --b 文件X --out 自检.json     同一个文件跟自己比，差异必须为 0（证明脚本本身可靠）
#   python check_tensors.py --a 官方shard1 --b SC117shard1 --out 对比.json
#   python check_tensors.py --filehash 某个gguf                     只算整文件 blake2b 和张量个数（用来比对两个 shard2）
import argparse, array, hashlib, json, os, struct, sys

SCALAR = {0:('<B',1), 1:('<b',1), 2:('<H',2), 3:('<h',2), 4:('<I',4), 5:('<i',4),
          6:('<f',4), 7:('<?',1), 10:('<Q',8), 11:('<q',8), 12:('<d',8)}

def rd_str(f):
    n = struct.unpack('<Q', f.read(8))[0]
    return f.read(n).decode('utf-8')

ARR = {0:('B',1), 1:('b',1), 2:('H',2), 3:('h',2), 4:('I',4), 5:('i',4),
       6:('f',4), 7:('B',1), 10:('Q',8), 11:('q',8), 12:('d',8)}
_arr_cache = {}

def rd_value(f, t, key=''):
    if t == 8:                      # string
        return rd_str(f)
    if t == 9:                      # array
        et = struct.unpack('<I', f.read(4))[0]
        n = struct.unpack('<Q', f.read(8))[0]
        if et == 8:                 # 字符串数组
            return [rd_str(f) for _ in range(n)]
        if et == 9:                 # 嵌套数组：整份跳掉，只统计个数
            return ['<嵌套数组 %d 个>' % n for _ in range(n)] if n == 0 else ['<嵌套数组>'] * n
        if et not in ARR:
            raise ValueError('数组元素类型不支持: key=%r elem_type=%d 个数=%d' % (key, et, n))
        tc, sz = ARR[et]
        a = array.array(tc)
        a.frombytes(f.read(sz * n))
        if sys.byteorder != 'little':
            a.byteswap()
        return a
    if t not in SCALAR:
        raise ValueError('kv 类型不支持: key=%r type=%d' % (key, t))
    fmt, sz = SCALAR[t]
    return struct.unpack(fmt, f.read(sz))[0]

def parse(path):
    """返回 (version, kv, {张量名: (dtype, 绝对偏移, 字节长度, 维度)}, 整文件blake2b)"""
    with open(path, 'rb') as f:
        if f.read(4) != b'GGUF':
            raise ValueError('不是 GGUF 文件: %s' % path)
        version = struct.unpack('<I', f.read(4))[0]
        n_tensors = struct.unpack('<Q', f.read(8))[0]
        n_kv = struct.unpack('<Q', f.read(8))[0]
        kv = {}
        for _ in range(n_kv):
            k = rd_str(f)
            t = struct.unpack('<I', f.read(4))[0]
            kv[k] = rd_value(f, t, k)
        align = int(kv.get('general.alignment', 32))
        infos = []
        for _ in range(n_tensors):
            name = rd_str(f)
            nd = struct.unpack('<I', f.read(4))[0]
            dims = tuple(struct.unpack('<Q', f.read(8))[0] for _ in range(nd))
            dt = struct.unpack('<I', f.read(4))[0]
            off = struct.unpack('<Q', f.read(8))[0]
            infos.append((name, dims, dt, off))
        hdr_end = f.tell()
    data_start = (hdr_end + align - 1) // align * align
    size = os.path.getsize(path)
    infos.sort(key=lambda x: x[3])
    tensors = {}
    for i, (name, dims, dt, off) in enumerate(infos):
        end = infos[i + 1][3] if i + 1 < len(infos) else (size - data_start)
        tensors[name] = (dt, data_start + off, end - off, dims)
    h = hashlib.blake2b(digest_size=32)
    with open(path, 'rb') as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            h.update(b)
    return version, kv, tensors, h.hexdigest()

def tensor_hash(path, off, ln):
    h = hashlib.blake2b(digest_size=32)
    with open(path, 'rb') as f:
        f.seek(off)
        left = ln
        while left > 0:
            b = f.read(min(1 << 22, left))
            if not b:
                break
            h.update(b)
            left -= len(b)
    return h.hexdigest()

FAMS = {'attn_output', 'ssm_out', 'ffn_down_shexp', 'ffn_down_exps'}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a'); ap.add_argument('--b'); ap.add_argument('--out')
    ap.add_argument('--filehash'); ap.add_argument('--expect-diff', type=int, default=144)
    args = ap.parse_args()

    if args.filehash:
        v, kv, t, fh = parse(args.filehash)
        print('文件:', args.filehash)
        print('GGUF 版本:', v, ' 张量个数:', len(t), ' 头长度 kv:', len(kv))
        print('整文件 blake2b:', fh)
        return

    va, kva, ta, fa = parse(args.a)
    vb, kvb, tb, fb = parse(args.b)
    only_a = sorted(set(ta) - set(tb))
    only_b = sorted(set(tb) - set(ta))
    common = sorted(set(ta) & set(tb))
    diffs = []
    same = 0
    for i, name in enumerate(common):
        dta, oa, la, da = ta[name]
        dtb, ob, lb, db = tb[name]
        if (dta, la, da) != (dtb, lb, db):
            diffs.append({'name': name, '原因': '类型或尺寸不同', 'a_dtype': dta, 'b_dtype': dtb,
                          'a_len': la, 'b_len': lb, 'a_dims': list(da), 'b_dims': list(db)})
        elif tensor_hash(args.a, oa, la) != tensor_hash(args.b, ob, lb):
            diffs.append({'name': name, '原因': '内容不同', 'a_dtype': dta, 'b_dtype': dtb, 'a_len': la})
        else:
            same += 1
        if (i + 1) % 200 == 0:
            print('  已比 %d/%d，差异 %d' % (i + 1, len(common), len(diffs)), flush=True)

    fam = {}
    for d in diffs:
        k = d['name'].split('.')[-2]      # 张量名都以 .weight 结尾，族名在倒数第二段
        fam[k] = fam.get(k, 0) + 1

    head_ok = True
    head_detail = {}
    for probe in ('token_embd.weight', 'output.weight'):
        if probe in ta and probe in tb:
            dta, oa, la, _ = ta[probe]
            dtb, ob, lb, _ = tb[probe]
            ok = tensor_hash(args.a, oa, la) == tensor_hash(args.b, ob, lb)
            head_detail[probe] = '未变' if ok else '被改了'
            head_ok = head_ok and ok

    chk = {
        '1 张量名个数一致': (not only_a and not only_b and len(ta) == len(tb)),
        '2 差异个数 == %d' % args.expect_diff: (len(diffs) == args.expect_diff),
        '3 差异只在这4族': all(d['name'].split('.')[-2] in FAMS for d in diffs),
        '4 输出头/词表未变': head_ok,
    }
    out = {
        'a': args.a, 'b': args.b,
        'a张量数': len(ta), 'b张量数': len(tb), '共同': len(common),
        'a整文件blake2b': fa, 'b整文件blake2b': fb,
        'only_in_a': only_a[:50], 'only_in_b': only_b[:50],
        '差异个数': len(diffs), '相同个数': same,
        '差异按族': fam, '输出头状态': head_detail,
        '差异清单': diffs, '判据': chk,
    }
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as w:
            json.dump(out, w, ensure_ascii=False, indent=1)
    print('张量数 A/B: %d/%d   共同 %d   不同 %d   相同 %d' % (len(ta), len(tb), len(common), len(diffs), same))
    print('差异按族:', fam)
    print('输出头状态:', head_detail)
    print('整文件哈希 A:', fa)
    print('整文件哈希 B:', fb)
    print('判据:')
    for k, v in chk.items():
        print('  ', k, '=>', '通过' if v else '不通过')
    if args.out:
        print('已写:', args.out)

main()
