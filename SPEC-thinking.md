# 规格：不同思考强度对能力的影响（2026-10-17）

## 1. 要做什么

本机模型（Qwen3.8-Flash-Next IQ3_XXS，引擎 0.1.44.1）支持四档思考强度：`none / low / medium / high`（默认 high）。
测这四档在**同一套题**上的正确率和速度，看「想得多」到底换来什么。

依据（`D:/Strata/Strata-main/docs/DETAILS.md` 第 702-713 行，逐字）：
- OpenAI 接口：`"reasoning_effort": "none" | "low" | "medium" | "high"`
- 「The levels are instructions the model was trained with, **not a hard token limit**: on easy questions all three think briefly, on hard ones `high` thinks longest and is most accurate.」
- 另有硬上限：请求里 `reasoning_budget_tokens: N`（**请求的值覆盖配置的值**）；本机配置里现在是 2000。

## 2. 接口（怎么发请求）

`POST http://127.0.0.1:8080/v1/chat/completions`
```
{"model":"qwen3.8-flash-next-iq3_xxs","temperature":0,"max_tokens":3000,
 "reasoning_effort":"low", "messages":[{"role":"user","content":"<题目>"}]}
```
返回里 `message.reasoning_content` = 思考内容，`message.content` = 答案。

## 3. 档位（写死）

| 档 | reasoning_effort | reasoning_budget_tokens |
|---|---|---|
| A | none | 不设（用配置的 2000，但 none 本来就不思考） |
| B | low | 2000 |
| C | medium | 2000 |
| D | high | 2000 |
| E | high | 0（**不封顶**，看默认 2000 的封顶有没有挡住 high） |

## 4. 题目（12 道，全部有唯一可机械判定的答案）

| # | 题目 | 正确答案 | 判法 |
|---|---|---|---|
| 1 | 23×47+19 = ? | 1100 | 数字相等 |
| 2 | 鸡兔同笼，头 35、脚 94，兔几只？ | 12 | 数字相等 |
| 3 | 一个数加 7、乘 3、减 6 得 30，这个数是多少？ | 5 | 数字相等 |
| 4 | 两枚骰子点数之和为 7 的概率，写成最简分数 | 1/6 | 匹配 `1/6` |
| 5 | 2026 年 10 月 17 日是星期几？ | 星期六 | 匹配 星期六/周六/Saturday |
| 6 | 把 banana, apple, cherry, date 按字母序排好，每行一个 | apple banana cherry date | 四行逐字比对 |
| 7 | 用 3、3、7、7 各一次和 + - * / 凑 24，写出算式 | 例 `7*(3+3/7)` | 脚本解析：四个数各用一次、结果 == 24 |
| 8 | 一台机器 5 分钟生产 5 个零件。100 台机器生产 100 个零件要几分钟？ | 5 | 数字相等（陷阱题） |
| 9 | A 比 B 高，B 比 C 高，C 比 D 高。谁最矮？ | D | 匹配 D |
| 10 | 从 5 个人里选 2 人，多少种组合？ | 10 | 数字相等 |
| 11 | 「所有玫瑰都是花；有些花是红的；所以有些玫瑰是红的」这个推理对不对？ | 不对（无效） | 匹配 不对/不正确/无效/no |
| 12 | 一本书第一天读一半多 10 页，第二天读剩下的一半，剩 20 页。全书多少页？ | 100 | 数字相等 |

## 5. 怎么算「能力」

- 每题跑 **2 次**（本机实测：同一状态连问两次答案会不同 → 单次不算数）。
- 每档正确率 = 判对的次数 / 24（12 题 × 2 次）。
- 同时记：思考长度（reasoning 的 token 数，取 usage 的 completion_tokens 与 content 长度差）、整题耗时、tok/s。
- **先测漂移**：同一档同一题两次结果不一致的比例就是噪声底，报告里必须给出来。

## 6. 怎么算做完

- 5 档 × 12 题 × 2 次 = **120 次请求**，全部跑完，结果存 `E:/Strata-bench/think-results.json`。
- 输出一张表：每档的正确率、平均思考长度、平均耗时。
- 结论必须说清测试环境（本机、IQ3_XXS、temperature 0、4k 无关、单请求）。
- 如果某两档正确率差 ≤ 1 题（噪声范围内）→ 老实说「测不出差别」。
