# -*- coding: utf-8 -*-
"""不同思考强度的能力测试。规格见 SPEC-thinking.md。只打印汇总，答案原文存 JSON。"""
import json, re, time, sys, urllib.request, ast, operator

URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "qwen3.8-flash-next-iq3_xxs"
OUT = r"E:\Strata-bench\think-results.jsonl"

LEVELS = {
    "A_none":   {"effort": "none"},
    "B_low":    {"effort": "low"},
    "C_medium": {"effort": "medium"},
    "D_high":   {"effort": "high"},
    "E_high_nocap": {"effort": "high", "budget": 0},
}

Q = [
    ("q1",  "计算 23×47+19，只给结果。", 1100),
    ("q2",  "鸡兔同笼，头共35个、脚共94只，兔有几只？只给数字。", 12),
    ("q3",  "一个数加上7，乘以3，减去6，结果是30。这个数是多少？只给数字。", 5),
    ("q4",  "两枚普通骰子点数之和为7的概率是多少？写成最简分数，例如 1/6。", "1/6"),
    ("q5",  "2026年10月17日是星期几？只回答星期几。", "星期六"),
    ("q6",  "把下面四个单词按字母序排列，每行一个，不要别的文字：\nbanana\napple\ncherry\ndate",
     ["apple", "banana", "cherry", "date"]),
    ("q7",  "用 3、3、7、7 各一次，配 + - * / 和括号凑出 24。只写一个算式。", "24expr"),
    ("q8",  "一台机器5分钟生产5个零件。100台机器生产100个零件需要多少分钟？只给数字。", 5),
    ("q9",  "A比B高，B比C高，C比D高。四人中最矮的是谁？只给字母。", "D"),
    ("q10", "从5个人里选出2个人，一共有多少种不同的组合？只给数字。", 10),
    ("q11", "前提：所有玫瑰都是花；有些花是红的。结论：有些玫瑰是红的。这个推理是否成立？只回答“成立”或“不成立”。", "不成立"),
    ("q12", "一本书，第一天读了一半多10页，第二天读了剩下的一半，还剩20页。这本书一共多少页？只给数字。", 100),
]

NUM = re.compile(r"-?\d+(?:\.\d+)?")
EXPR = re.compile(r"\d[\d\s\.\+\-\*/\(\)×÷]*\d")
OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}


def last_number(text):
    ns = NUM.findall(text or "")
    return float(ns[-1]) if ns else None


def check(qid, expected, content):
    c = (content or "").strip()
    if isinstance(expected, list):
        lines = [l.strip().lower() for l in c.splitlines() if l.strip()]
        return lines == [e.lower() for e in expected]
    if expected == "24expr":
        for m in EXPR.findall(c):
            s = m.replace("×", "*").replace("÷", "/")
            try:
                val = eval(s, {"__builtins__": {}}, {})
            except Exception:
                continue
            if abs(val - 24) < 1e-9 and sorted(NUM.findall(s)) == ["3", "3", "7", "7"]:
                return True
        return False
    if expected == "1/6":
        return "1/6" in c.replace(" ", "")
    if expected == "星期六":
        return bool(re.search(r"星期六|周六|星期六|Saturday", c, re.I))
    if expected == "不成立":
        return "不成立" in c or "不 成立" in c
    if isinstance(expected, str):
        return expected.strip().lower() in c.lower()
    n = last_number(c)
    return n is not None and abs(n - expected) < 1e-6


def ask(prompt, level):
    cfg = LEVELS[level]
    body = {"model": MODEL, "temperature": 0, "max_tokens": 2500,
            "reasoning_effort": cfg["effort"],
            "messages": [{"role": "user", "content": prompt}]}
    if "budget" in cfg:
        body["reasoning_budget_tokens"] = cfg["budget"]
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    d = json.load(urllib.request.urlopen(req, timeout=600))
    wall = time.time() - t0
    ch = d["choices"][0]
    msg = ch["message"]
    reasoning = msg.get("reasoning_content") or ""
    content = msg.get("content") or ""
    usage = d.get("usage", {})
    return {
        "wall_s": round(wall, 2),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_chars": len(reasoning),
        "content_chars": len(content),
        "finish": ch.get("finish_reason"),
        "ok": None,
        "content": content,
        "reasoning": reasoning,
    }


def main():
    level = sys.argv[1]
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    recs = []
    for qid, prompt, expected in Q:
        for r in range(runs):
            rec = ask(prompt, level)
            rec.update({"level": level, "qid": qid, "run": r})
            try:
                rec["ok"] = bool(check(qid, expected, rec["content"]))
            except Exception as e:
                rec["ok"] = False
                rec["check_error"] = str(e)
            recs.append(rec)
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print("%s %s run%d ok=%s wall=%.1fs think_chars=%d total_tok=%s"
                  % (level, qid, r, rec["ok"], rec["wall_s"], rec["reasoning_chars"],
                     rec["completion_tokens"]), flush=True)
    good = sum(1 for x in recs if x["ok"])
    walls = [x["wall_s"] for x in recs]
    th = [x["reasoning_chars"] for x in recs]
    print("SUMMARY %s: %d/%d correct, avg wall %.1fs, avg reasoning chars %.0f"
          % (level, good, len(recs), sum(walls) / len(walls), sum(th) / len(th)))


if __name__ == "__main__":
    main()
