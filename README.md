# Strata 引擎调优实验场（strata-bench）

## 这是什么

本机那个「助手的大脑」——`127.0.0.1:8080` 上的 Strata 引擎（模型 Qwen3.8-Flash-Next IQ3_XXS）——的**调参与测速实验场**。
所有开关该开还是该关、哪个量化档能不能用、速度到底多少，**结论都出自这个文件夹的实测**，别凭印象报数字。

## 先搞清楚哪个是「真身」（最容易搞错的一条）

| 树 | 是什么 |
|---|---|
| `D:\Strata\Strata-main` | **当前唯一在跑的引擎**（0.1.46，`--vram-reserve-mib 1536`、`--max-context 262144`） |
| `D:\Strata\Strata-0.1.45-backup` | 上一版完整备份，退回老引擎用它 |
| 本目录 `new\`、`stage-engine-0.1.45\`、`engine-backup-0.1.44.1\`、`old_engine_backup\` | **历史引擎副本，都不在跑**，只作对照/回滚 |

## 怎么启动 / 怎么测

- 起引擎：双击桌面「**启动新版引擎.bat**」或 `D:\Strata\Strata-main\START-HERE.bat`（改配置必须重启才生效）。
- 测速：`python bench_new.py` —— 停旧 → 起新(8081) → 测 → 停新 → 恢复旧(8080)，一条命令跑通。
- 单独测某组参数：`bench_combo.py` / `bench_overlap.py` / `bench_prefill.py` / `bench_unbuf.py`；只重启不测用 `restart_engine.py`。
- **测之前必须先停引擎**：12G 显存装不下两个（旧引擎常驻 11.4/12.2 GB）。
- 当前执行中的调参单：`tune-spec.md`（跟着它走）。

## 结果和结论在哪

- `PROGRESS.md` —— 全部过程与**踩过的坑**（最重要，动手前先读开头那节）。
- `BENCH_RESULT.txt` —— 新旧引擎对比结论；`QUANTS.md` —— 各量化档实测；`tune-result.md` / `tune-report-raw.json` —— 调参结果。
- 根目录那一百多个 `*.json` / `*.log` 是历次跑的原始数据，**不用清理也不用读**，要引用数字时按文件名找（`-4k` / `-16k` / `pf-` 开头分别是上下文档位和 prefill 测试）。

## 硬规矩

1. 数字必须带测试环境（这台机器、这个档位、这个上下文），别当通用结论讲。
2. 换档/调参 = 同种子 A/B，一次只改一个变量，判据在 `ab-test-zh` 技能。
3. `--max-context` 和 `kv-resident` 老大已定不动，别再提议。
