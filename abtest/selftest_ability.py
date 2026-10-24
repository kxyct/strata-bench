# 判分器自检：不发请求给模型，直接把「理想答案」喂给判分器，必须 40/40 全对。
# 判分器自己有毛病的话，第三关会把对的判成错的，所以这一步必须先过。
# 用法： python selftest_ability.py
import test_ability as T

CODE_IDEAL = [
    "```python\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n```",
    "```python\ndef reverse_words(s):\n    return ' '.join(s.split()[::-1])\n```",
    "```python\ndef is_palindrome(s):\n    t = ''.join(c.lower() for c in s)\n    return t == t[::-1]\n```",
    "```python\ndef count_vowels(s):\n    return sum(1 for c in s.lower() if c in 'aeiou')\n```",
    "```python\ndef second_largest(nums):\n    u = sorted(set(nums))\n    return u[-2]\n```",
    "```python\ndef flatten(lst):\n    out = []\n    for x in lst:\n        if isinstance(x, list):\n            out.extend(x)\n        else:\n            out.append(x)\n    return out\n```",
    "```python\ndef roman_to_int(s):\n    v = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}\n    total = 0\n    for i, c in enumerate(s):\n        n = v[c]\n        if i + 1 < len(s) and v[s[i+1]] > n:\n            total -= n\n        else:\n            total += n\n    return total\n```",
]

FOLLOW_IDEAL = ["6\n6\n3", '{"a": 1, "b": 2}', "你\n好\n世\n界", "EDCBA", "1,2,3,4,5"]

def ideal_for(t):
    k = t["spec"]["判"]
    if k == "num":
        return str(t["spec"]["期望"])
    if k == "contains":
        return "答案是 " + t["spec"]["关键词"][0]
    if k == "code":
        return None
    if k == "lines_numbers":
        return "6\n6\n3"
    if k == "json_keys":
        return '{"a": 1, "b": 2}'
    if k == "lines_count":
        return "你\n好\n世\n界"
    if k == "exact":
        return t["spec"]["期望"]
    if k == "exact_norm":
        return t["spec"]["期望"]
    return None

bank = T.build_bank()
code_i = 0
follow_i = 0
ok_n = 0
bad = []
for t in bank:
    if t["spec"]["判"] == "code":
        ans = CODE_IDEAL[code_i]
        code_i += 1
        spec = dict(t["spec"]); spec["ans"] = ans
        ok, why = T.run_code(t["问题"], spec, t["类"])
    else:
        if t["类"] == "指令跟随":
            ans = FOLLOW_IDEAL[follow_i]
            follow_i += 1
        else:
            ans = ideal_for(t)
        ok, why = T.score(dict(t["spec"], ans=ans), ans)
    ok_n += 1 if ok else 0
    if not ok:
        bad.append((t["类"], t["问题"][:30], why))

print("题数:", len(bank), " 判分器自检通过:", ok_n)
if bad:
    print("判分器有毛病，这些题的理想答案被判错：")
    for b in bad:
        print("  [%s] %s  ->  %s" % b)
    raise SystemExit(1)
print("判分器自检全绿，第三关可以开跑")
