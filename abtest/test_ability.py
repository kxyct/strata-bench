# 第三关：能力测试（40 题全部自动判分，跑 3 轮算噪声带）
# 用法： python test_ability.py --host http://127.0.0.1:8080 --runs 3 --out 能力结果.json
# 硬要求：并发 1；两个模型不能同时跑，换模型后各跑一次本脚本
import argparse, json, os, re, subprocess, sys, tempfile, time, urllib.request

def num_expect(v, tol=1e-3): return {"判": "num", "期望": v, "容差": tol}
def any_of(*ks): return {"判": "contains", "关键词": list(ks)}

MATH = [
    ("2,3,5,8,13,21 的下一项是多少？只回答数字。", num_expect(34)),
    ("37 乘以 89 等于多少？只回答数字。", num_expect(3293)),
    ("四分之一加六分之一等于多少？只回答小数，保留 4 位。", num_expect(5/12, 1e-3)),
    ("进水管 3 小时注满水池，出水管 6 小时排空，两个同时开，几小时注满？只回答数字。", num_expect(6)),
    ("一个最小正整数除以 7 余 3、除以 5 余 2，它是多少？只回答数字。", num_expect(17)),
    ("17 的阶乘末尾有几个 0？只回答数字。", num_expect(3)),
    ("从 5 个人里选 3 个人有多少种组合？只回答数字。", num_expect(10)),
    ("掷两枚骰子点数之和为 7 的概率是多少？只回答分数或小数。", num_expect(1/6, 1e-3)),
    ("等差数列首项 3、公差 4，第 20 项是多少？只回答数字。", num_expect(79)),
    ("矩形周长 34，长比宽大 3，面积是多少？只回答数字。", num_expect(70)),
    ("100 以内能同时被 3 和 5 整除的数有几个？只回答数字。", num_expect(6)),
    ("60 千米每小时等于多少米每秒？只回答数字，保留 2 位小数。", num_expect(16.67, 0.05)),
    ("1000 元年利率 10%，复利两年后本利和是多少？只回答数字。", num_expect(1210)),
    ("log2(1024) 等于多少？只回答数字。", num_expect(10)),
    ("袋中 3 红 2 蓝，不放回取两球同色的概率？只回答小数，保留 2 位。", num_expect(0.40, 0.02)),
]

CODE = [
    ("写一个函数 fib(n)，返回斐波那契第 n 项（fib(0)=0, fib(1)=1）。只输出代码。",
     "assert fib(10)==55\nassert fib(0)==0\n"),
    ("写一个函数 reverse_words(s)，反转单词顺序、单词内部不变。只输出代码。",
     'assert reverse_words("a b c")=="c b a"\n'),
    ("写一个函数 is_palindrome(s)，忽略大小写判断回文。只输出代码。",
     'assert is_palindrome("Rotator") and not is_palindrome("abc")\n'),
    ("写一个函数 count_vowels(s)，统计元音字母个数。只输出代码。",
     'assert count_vowels("hello world")==3\n'),
    ("写一个函数 second_largest(nums)，返回第二大的不同数值。只输出代码。",
     "assert second_largest([5,1,9,9,3])==5\n"),
    ("写一个函数 flatten(lst)，把一层嵌套的列表拉平。只输出代码。",
     "assert flatten([1,[2,3],[4]])==[1,2,3,4]\n"),
    ("写一个函数 roman_to_int(s)，罗马数字转整数。只输出代码。",
     'assert roman_to_int("MCMXCIV")==1994\n'),
]

ZH = [
    ("“他气得说不出话来”里的“得”属于什么词性？只回答一个词：助词/介词/动词/名词/形容词/副词。", any_of("助")),
    ("“兵不厌诈”是什么意思？", any_of("欺骗", "欺诈", "诈")),
    ("把“他很聪明，但是不努力”改写成一个用“虽然”的转折句。", any_of("虽然")),
    ("“菽”指的是哪类作物？", any_of("豆")),
    ("《西游记》的作者是谁？", any_of("吴承恩")),
    ("三点水加“去”是什么字？", any_of("法")),
    ("“请把窗户关上”是什么句式？", any_of("祈使")),
    ("“因为下雨，所以地湿”，地湿的原因是什么？", any_of("下雨")),
]

FOLLOW = [
    ("只输出恰好三行：第一行是 1、2、3 的和，第二行是它们的积，第三行是最大值。",
     {"判": "lines_numbers", "期望": [6, 6, 3]}),
    ("只输出一个 JSON 对象，键 a 的值是 1，键 b 的值是 2。", {"判": "json_keys", "期望": {"a": 1, "b": 2}}),
    ("把“你好世界”四个字每字一行输出，不要别的内容。", {"判": "lines_count", "期望": 4}),
    ("只输出字母 ABCDE 的逆序。", {"判": "exact", "期望": "EDCBA"}),
    ("只输出 1 到 5，用英文逗号分隔，不要别的内容。", {"判": "exact_norm", "期望": "1,2,3,4,5"}),
]

def filler(mark, value):
    """造一段约 4000 字的固定背景文本，把标记插在中间（内容固定，不随机）"""
    base = ["这是一段用于长上下文测试的固定段落。", "系统日志记录了一次例行巡检的结果。",
            "下面是会议记录的一部分，与本题无关。", "该段落仅用于占位，不提供任何信息。",
            "运维团队按流程完成了当天的检查项。"]
    parts = []
    for i in range(30):
        for b in base:
            parts.append("%s（第 %d 段）" % (b, i))
        if i == 15:
            parts.append("特别注意：%s 是 %s。" % (mark, value))
    return "\n".join(parts)

LONG = [
    ("上面的材料里，“内部编号”是多少？只回答编号本身。", ("内部编号", "KR-4471"), any_of("4471")),
    ("上面的材料里，会议改到了几月几日？只回答日期。", ("会议改到", "11 月 26 日"), any_of("26")),
    ("上面的材料里提到的预算金额是多少元？只回答数字。", ("预算", "84200 元"), any_of("84200")),
    ("上面的材料里指定的联系人是谁？只回答姓名。", ("联系人", "周敏"), any_of("周敏")),
    ("上面的材料里设备序列号的后四位数字是什么？只回答数字。", ("设备序列号", "ZQ77-8802"), any_of("8802")),
]

SAFE_FORBID = re.compile(r"\b(os|subprocess|sys|shutil|socket|ctypes|eval|exec|open|__import__)\b")

def model_name(host):
    with urllib.request.urlopen(host + "/v1/models", timeout=30) as r:
        return json.load(r)["data"][0]["id"]

def ask(host, mname, prompt, max_tokens=600):
    body = json.dumps({"model": mname, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0, "max_tokens": max_tokens}).encode("utf-8")
    req = urllib.request.Request(host + "/v1/chat/completions", data=body,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    return (d["choices"][0]["message"]["content"] or "").strip()

def last_num(text):
    m = re.search(r"(-?\d+)\s*/\s*(-?\d+)(?!\d)", text)
    if m:
        try:
            a, b = int(m.group(1)), int(m.group(2))
            if b: return a / b
        except Exception:
            pass
    nums = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not nums: return None
    try: return float(nums[-1])
    except Exception: return None

def grab_code(text):
    m = re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.S)
    if m:
        return max(m, key=len)
    return text

def score(item, ans):
    kind = item["判"]
    if kind == "num":
        v = last_num(ans)
        return v is not None and abs(v - item["期望"]) <= item["容差"], "抽出数字=%r" % v
    if kind == "contains":
        hit = [k for k in item["关键词"] if k in ans]
        return bool(hit), "命中=%s" % hit
    if kind == "exact":
        return ans.strip() == item["期望"], "原文=%r" % ans[:60]
    if kind == "exact_norm":
        return re.sub(r"\s+", "", ans) == item["期望"], "原文=%r" % ans[:60]
    if kind == "lines_count":
        ls = [l for l in ans.splitlines() if l.strip()]
        return len(ls) == item["期望"], "行数=%d" % len(ls)
    if kind == "lines_numbers":
        ls = [l.strip() for l in ans.splitlines() if l.strip()]
        got = [last_num(l) for l in ls]
        return len(ls) == len(item["期望"]) and got == item["期望"], "行数字=%r" % got
    if kind == "json_keys":
        m = re.search(r"\{.*\}", ans, re.S)
        if not m: return False, "找不到 JSON"
        try:
            d = json.loads(m.group(0))
        except Exception as e:
            return False, "JSON 解析失败 %s" % e
        return d == item["期望"], "解析=%r" % d
    return False, "未知判分方式"

def run_code(q, spec, tag):
    code = grab_code(spec["ans"])
    if SAFE_FORBID.search(code):
        return False, "生成的代码含受限内容，未执行"
    d = tempfile.mkdtemp(prefix="abtest_")
    p = os.path.join(d, "t.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(code + "\n" + spec["断言"])
    try:
        r = subprocess.run([sys.executable, p], capture_output=True, text=True, timeout=8)
        return r.returncode == 0, "rc=%d %s" % (r.returncode, (r.stderr or "")[-120:].replace("\n", " "))
    except subprocess.TimeoutExpired:
        return False, "超时 8 秒"
    except Exception as e:
        return False, "执行异常 %s" % e

def build_bank():
    bank = []
    for q, spec in MATH:
        bank.append({"类": "数学", "问题": q, "spec": dict(spec, ans="")})
    for q, asserts in CODE:
        bank.append({"类": "代码", "问题": q + "\n要求：纯函数，不要读文件、不要联网、不要 import 任何模块。",
                     "spec": {"判": "code", "断言": asserts, "ans": ""}})
    for q, spec in ZH:
        bank.append({"类": "中文", "问题": q, "spec": dict(spec, ans="")})
    for q, spec in FOLLOW:
        bank.append({"类": "指令跟随", "问题": q, "spec": dict(spec, ans="")})
    for q, (mark, val), spec in LONG:
        ctx = filler(mark, val)
        bank.append({"类": "长上下文", "问题": ctx + "\n\n" + q, "spec": dict(spec, ans=""),
                     "标记": "%s=%s" % (mark, val)})
    return bank

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://127.0.0.1:8080")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    mname = model_name(a.host)
    bank = build_bank()
    counts = {}
    for t in bank:
        counts[t["类"]] = counts.get(t["类"], 0) + 1
    print("被测模型:", mname, " 题数:", len(bank), counts)
    rounds = []
    for rd in range(a.runs):
        got = 0
        detail = []
        for i, t in enumerate(bank):
            try:
                ans = ask(a.host, mname, t["问题"])
            except Exception as e:
                detail.append({"类": t["类"], "i": i, "对": False, "说明": "请求失败 %s" % e})
                continue
            spec = dict(t["spec"]); spec["ans"] = ans
            if spec["判"] == "code":
                ok, why = run_code(t["问题"], spec, t["类"])
            else:
                ok, why = score(spec, ans)
            got += 1 if ok else 0
            detail.append({"类": t["类"], "i": i, "对": ok, "说明": why,
                           "答前60字": ans[:60].replace("\n", " ")})
            print("  第 %d 轮 %d/%d [%s] %s" % (rd + 1, i + 1, len(bank), t["类"], "对" if ok else "错"), flush=True)
            time.sleep(0.2)
        by = {}
        for d in detail:
            by.setdefault(d["类"], [0, 0])
            by[d["类"]][0] += 1
            by[d["类"]][1] += 1 if d["对"] else 0
        rounds.append({"轮": rd + 1, "得分": got, "总分": len(bank), "分类": by, "明细": detail})
        print("第 %d 轮得分: %d/%d" % (rd + 1, got, len(bank)))
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                json.dump({"模型": mname, "轮数": a.runs, "分类题数": counts, "轮次": rounds}, f,
                          ensure_ascii=False, indent=1)
    scores = [r["得分"] for r in rounds]
    mean = sum(scores) / len(scores)
    band = max(scores) - min(scores)
    print("\n=== 汇总 ===")
    print("各轮得分:", scores)
    print("均值 %.2f / %d，本机噪声带（最大最小差）= %d" % (mean, len(bank), band))
    print("分类均值:")
    for c, n in counts.items():
        cs = [r["分类"].get(c, [0, 0])[1] for r in rounds]
        print("  %-8s %d 题  均值 %.2f" % (c, n, sum(cs) / len(cs)))
    print("结论规则：换模型后，只有均值差大于本机噪声带 %d 分才算真的变化" % band)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"模型": mname, "轮数": a.runs, "分类题数": counts, "各轮得分": scores,
                       "均值": mean, "噪声带": band, "轮次": rounds}, f, ensure_ascii=False, indent=1)
        print("已写:", a.out)

if __name__ == "__main__":
    main()
