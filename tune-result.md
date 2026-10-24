# Strata 官方自动调参第一轮结果（2026-10-21 凌晨，quick 快档）

## 怎么跑的
- 命令：`strata.py tune auto --mode quick --goal speed --name tune1021 --serve-dir D:\Strata\Strata-main <咱的 run-config json>`
- 环境：本机 12G 5070Ti / 引擎 0.1.46 / 咱现役配置（reserve 1536、spec 4、adapt 开、kv-resident 32768）；测前引擎已停干净
- 实际用时 5.3 分钟（quick 档，1 次测量运行），产物：`tune-report-raw.json`（它自己 stdout 的完整 JSON）

## 结果原文（直译）
- **结论码：`default_confirmed` / `already_fastest`（当前设置已是最快）**，baseline 实测 **65.0 tok/s**（与咱日常实测 ~65 完全吻合，两边互相印证）
- **但本轮实际测量的候选 = 0 个**——9 个候选全部被它的策略拦下，原因逐条在案：

| 候选 | 它拦下的原因 |
|---|---|
| adapt_async（后台学习留哪些专家） | 每次跑结果都不同，要勾「允许不可复现」才测 |
| spec3（投机窗口缩短到 3） | 可能轻微改变回答，要勾「允许小差异」才测 |
| adapt_tier_fast / adapt_decay_09（缓存自适应档位/衰减） | 同上，要勾「允许小差异」 |
| trim_stage | 本机不符合条件（双 GPU 项） |
| kv_resident_64k | 快档时间预算装不下，留给 thorough |
| pin_by_need / host_core_last / kv_grow | **它自己 thorough 历史轮已测过 = 无增益（flat）**，引用存档记录 |

- 顺带采到的本机事实（它独立测的）：槽 1126、pcie_frac 0.15、chunk 2560、可用内存 51.8 GiB、已装 39.97 GiB、咱的 17 个参数它全部认识（unknown_argument: false）
- preset「tune1021」已在 app 侧存档（不影响咱 json，咱引擎启动不走 app preset：`STRATA_NO_PRESET`）

## 怎么看这个结论
「已是最快」这句话本轮只对「可复现、不改回答」的参数成立——那批它测不动的（spec3、两个 adapt 项、64K 常驻）一个都没真测。要不要补测等老大拍板（见 PROGRESS 10.33 追加节）；**咱现役配置零改动**，第一轮无任何写盘。
