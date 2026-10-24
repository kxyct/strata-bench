# Strata 新旧引擎基准（2026-10-16）

## 现在做到哪（2026-10-21 凌晨更新）
**老大拍板「只要 app 的调参」（10-20 深夜），执行单 = `strata-bench/tune-spec.md`。当前进度：S1/S2/S3 已完成，等老大在 app 界面确认模型页不再报错。** app 白名单指纹表已改（两份 copies + .bak 备份，见 10.33），app 自己的代码已验通过、且「already_set_up」认下咱现成的 pack/MTP（不用重建）。下一步 = S4 确认数据接轨 + S5 跑 tune（**tune 前要停咱引擎** = 老大双击 stop-strata.bat 或助手延时点火）。
观察窗并行事项不变：0.1.46@reserve 1536 在 `D:\Strata\Strata-main` 运行，观察窗至 10-22，没事就在 10.29 末尾写「定案」。撤回 app 补丁 = 还原 .bak；撤回 app 本体 = uninstall.exe。
（历史：旧 0.1.41 vs 0.1.44.1 对比在 BENCH_RESULT.txt；10.16~10.28 各节 = 崩速诊断、0.2.1 测试栈、0.1.46 转正、搬树 D:\Strata。）

## 已经做完的
- 下载 0.1.44.1 主包（148 MB，SHA256 校验通过）→ 解压在 `new\`
- 测速脚本：复制 `D:\Strata\bench-submission\measure_parallel.py`，加了 `--host` 参数
- 旧引擎（8080）：decode 78.8 / prefill 913.6 / e2e 32.8 / hit 60.4%
- 新引擎（8081，`iq3_xxs_new.json` 配置）：decode 82.4 / prefill 922.8 / e2e 33.4 / hit 66.2%
- 自动化脚本 `bench_new.py`：停旧 → 起新(8081) → 测 → 停新 → 恢复旧(8080)，一次跑通

## 踩过的坑（别再踩）
1. **显存装不下两个引擎**（旧引擎常驻 11.4/12.2 GB）→ 必须排队测，不能并行。
2. **新下载的 strata.exe 第一次被杀软拦**（server 报 WinError 5 拒绝访问）→ 手动跑一次 `strata.exe --version` 放行后即可。
3. **taskkill /IM strata.exe 会连旧引擎一起杀**（新旧同名）→ 只想杀新引擎时按 ExecutablePath 筛 PID。
4. 测旧引擎要在助手的工具调用间隙跑（引擎一次只处理一个请求），脚本里先 sleep 25 秒让助手把消息发完。
5. Git Bash 里 PowerShell 的 WQL 引号会被吃掉 → `-Filter "Name='strata.exe'"` 这种写法要改用 Where-Object。

## 调参 A/B 结论（2026-10-16，全部本机 4k/16k 实测）
- ~~**STRATA_ADAPT_OVERLAP=1：采纳**~~ → **已推翻（2026-10-16 晚，见下面「overlap 关掉实测」）**：那个 82.4→86.0 是跨重启比较，方法不成立；官方 0.1.43.1 明确点名 RTX 5070 Ti 开 overlap **-21%**。现在配置里是 `STRATA_ADAPT_OVERLAP=0`。基线链 0.1.41=78.8 → 0.1.44.1=82.4 → ~~+overlap=86.0~~ 作废。
- **STRATA_UNBUFFERED_LOAD=1：拒绝**（16k prefill 1090.5 vs 1089.8 完全持平，decode 略降；官方"翻倍"在本机不成立）
- 基线链：0.1.41=78.8 → 0.1.44.1=82.4 → +overlap=86.0（累计 +9.1%）
- 未测：STRATA_ADAPT_SIGNAL=copy、--spec/--spec-min-p 微调（收益预期小，暂停）
- **大页内存：已否决（老大 2026-10-16 晚：「不要了，不好用」）**。权限授予 + 重启电脑后大页确实生效了（日志 `large pages are resident without a lock`），但实测 decode 中位 **80.4 / 73.2 / 74.6 / 76.9 tok/s**（`largepage-4k.json` / `lp3` / `lp4` / `lp5`，本机 4k、concurrent 1、runs 3、overlap=1）**全部低于不开大页的基线 86.0** → 大页更慢，别再试。
- **关掉大页的正确做法（不用管理员、不用重启电脑）**：正式配置 `D:\Strata\Strata-main\strata-iq3_xxs.json` 的 `env` 里加 `"STRATA_NO_LARGEPAGES": "1"`（引擎自带的 A/B 开关，见 `src/core/pinned.cu:88`）。2026-10-16 已加。生效需要重启引擎；生效判据 = 引擎日志出现 `large pages skipped (STRATA_NO_LARGEPAGES); using 4 KB pages`。撤回 = 删掉这一行。
- Windows 侧「锁定内存页」权限**保留不动**：老大已用 secedit 授予，引擎不去要 large pages 时它完全惰性；真要撤销需要管理员 + 注销重登，代价大、收益 0。
- **重启引擎后实测：大页确实被跳过**（日志 `large pages skipped (STRATA_NO_LARGEPAGES); using 4 KB pages`），但 decode 中位只有 **76.7 tok/s**（20:51 三轮 74.9 + 20:52 五轮 76.7，4k、concurrent 1），**没有回到 86.0**。同期 GPU 采样：70-79°C、100-130 W、SM 2450-2707 MHz → 没有明显降频，不是过热；当时空闲内存只剩 5.7 GB（strata 工作集 45.6 GB）。**未验证的判断**：跑基准的那个助手会话本身上下文已经很长，引擎要同时养它的 KV，基准请求跟它抢内存/缓存 → 数字偏低。**要可比数字必须重启引擎 + 开一个短上下文的新会话再测**；别把 76.7 当成「关大页把速度弄坏了」。
- **基准噪声实测**：同配置（overlap=1）两轮中位 86.0 vs 81.3，波动 ±5% → 最终判定要多轮+多指标同向，别拿单次下结论。
- unbuffered 已默认生效的日志证据：`expert arena read unbuffered (0-1 of 16 probe reads from the file cache)` —— 这就是 STRATA_UNBUFFERED_LOAD 无效的真正原因，与大页无关。
- secedit /export 也要管理员权限（rc=740），普通会话无法验证策略。
- **secedit 大坑（2026-10-16 实测）**：① 未授予的权限不会出现在 export 里 → 「导出改一行再导回」找不到目标行，必然失败；② 本机 export 的 SeServiceLogonRight 含坏账号「***无法访问***」（已删除账号），整份导回报「帐户名与安全标识间无任何映射完成」rc=1。正解：**最小 inf**（只写目标权限一行，其它权限不列 = 不动）。signature 行用 PowerShell 单引号数组写，避免反引号粘贴被吃。
- 权限授予后必须**注销重登或重启**才进新登录令牌；重启引擎无效（token 继承）。老大已重启过一次（19:40），当时授权没写进去，白重启。

- **第 1 项 A/B 已完成（2026-10-16 晚）：`--pcie-frac 0.20` 已删，保留引擎自动测的值 → 结论：保留自动值。**
  - 切换生效已证明（启动日志）：`PCIe probe: 14.4 GB/s host->device -> pcie_frac 0.40 (default 0.55)`，随后 `the CPU pool takes 39 us per missed expert (44.3 GB/s of expert bytes), the link 14.4 GB/s -> pcie_frac 0.15`。**本机自动值 = 0.15**（不是写死的 0.20）。
  - **同一个引擎、同一时刻、只换这一个变量**的交错 A/B（`measure_parallel.py` 新加了 `--tune`，走 server 的 `strata_tune`，见 `serve/server.py:962`「engine settings for this request only, measured without a restart」）：4 组中位 decode —— 0.20：78.7 / 78.9 / 80.0 / 80.1；0.15：80.4 / 81.3 / 82.2 / 80.3。**4 组里 3 组 0.15 更快，1 组持平，平均约 +2%** → 保留自动值。
  - **重要纠正**：重启后看到的 75.4 → 85.9（+14%）**不是份额的功劳**，是引擎重启后重新热身/自适应的功劳（5 轮里第 1 轮 74~77、后面几轮 85~89；3 轮的组只能爬到 78~81）。**判性能必须看交错对比，不能看「重启前 vs 重启后」。**
  - 弱点（别当成铁证）：引擎日志不逐请求打印份额，所以「请求带的 strata_tune 真被引擎采纳」没有日志直接证据，只有 server 代码注释 + 4 组方向一致。
  - 撤回 = 在 args 里加回 `"--pcie-frac", "0.20"` 两行。数据文件：`before-pcie020-4k.json`、`after-pcieauto-4k.json`、`after-pcieauto2-4k.json`、`ab1..ab4-*.json`。

- **第 2 项 `STRATA_HC_Q8=1`：判定为「本机不适用」，没做 A/B（省掉一次重启）。** 依据：pack 索引 `D:\Strata\Strata-data\packs\iq3_xxs\index.txt` 里超连接张量（`blk.N.hc_attn_down/up/inject`、`blk.N.hc_ffn_down/up/inject`、`output_hc_down/up`）的字节数正好是 2 字节/元素（10240×320 = 3,276,800 元素 → 6,553,600 字节 = BF16；Q8_0 会是 3,686,400 字节），**文件里没有 Q8_0 的超连接副本**；而这个开关读的就是「文件自带的 Q8_0 字节」（`src/core/native_dense.cpp:45` 的 `hc_q8_name` + `:329` 的 dtype 过滤），没有就空转。官方也只在 Unsloth 的 UD-* 文件上默认开它。顺带：`STRATA_HC_Q8_INJECT=1` 是「自己造一份 Q8_0 副本」的另一条路，会改变答案，没试。

- **第二遍读更新已完成（2026-10-16 晚，老大「再看看更新」）**：最新 release 就是 **v0.1.44.1**（列表前 5：44.1 / 44 / 43.1 / 43 / 42），**没有更新的版本**。上一遍被 `head -45` 截掉的 0.1.43 / 0.1.43.1 / 0.1.44 已补读。
  - **纠正（推翻我之前的说法）**：`STRATA_ADAPT_OVERLAP` 不是「0.1.43.1 起默认开」。原文：0.1.43 只在 **Linux NVIDIA** 默认开（Windows 当时就是 opt-in，因为「RTX 5070 上开着反而 Q2_0 慢 2.6%」）；0.1.43.1 又把它**在所有平台改回默认关**（#2010/#2011，回调线程挤在同一核上导致 decode 崩）。→ **我们配置里的 `STRATA_ADAPT_OVERLAP=1` 是真正的显式开启，不是冗余行**，别删。
  - **已用上的（本机已生效，有日志或二进制证据）**：route tail skip（日志 `1783333 missed experts skipped`）、自动测 PCIe 份额（刚启用）、adaptive overlap（我们的 =1）、commit batch、Windows 下 GGUF 就地并行读专家（0.1.43 修复，本机正是 GGUF 就地 + 64G）、长提示词不再被自动切 mmap / 看门狗不再误杀（0.1.43.1 修复）、长对话里的图片不再丢缓存（0.1.44 #2228，vision 开着）、`strata_kq.dll` 已随包到位。
  - **新候选第 3 项 `--adapt-async 1`（推荐先试）**：官方就在 **RTX 5070 + Windows** 上测的（Q2_0、arena 单卡、5 组交错、3 个批次）decode **+4.2~5.2%（15 组里 13 组更快）**，代码/文档类 prompt **+7~10%**，故事类持平。本机证据：live help 有这条且写明「resident RAM mode 或 arena（单卡）opt-in」，我们的 args 里没有 → **现在是关的**。代价：官方说「开了之后答案与阻塞版有微小差异」。
  - **新候选第 4 项 `STRATA_PIN_BY_NEED=1`（env，Windows/WDDM 专用）**：官方在 5070 实测 **prompt 读 +4.4%（5/5 组）**，配 `STRATA_ARENA_PIN_GIB=16` 时 **+8.5%**，decode ±1%。本机证据：引擎二进制里有这个 env 名（3 处）；日志显示本机 **整块 arena 的 cudaHostRegister 失败（out of memory），只钉住了 33 个 slice = 25 GiB 的前缀** → 正是这个开关要改的东西。它只改「钉哪些内存」的顺序，不改答案。
  - **不推荐换 IQ3_S**：0.1.44 把 64 GB 机器的默认档换成 IQ3_S（对 Q8_0 同 top-token 率 87.7% vs IQ3_XXS 84.5%），但 0.1.44.1 明说 **IQ3_S 比 IQ3_XXS 慢 10~15%、多用约 7 GB 内存**，并且修好了「重跑 setup 会擅自换档」。本机跑基准时空闲内存只剩 5.7 GB（工作集 45.6 GB）→ **换档装不下，不换**。
  - **不适用**：`STRATA_HC_Q8`（第 2 项，已判定）、UD-*/NVFP4/Qwen3.6-35B（本机没有这些文件）、Mac/AMD/Intel 全部条目、CUDA 12.0/12.1 编译修复（本机 CUDA 13.0）、`--prefill-head-alias`（给 8 GB 卡的）、`enable_large_pages.ps1`（老大已否决大页，**别跑这个脚本**）。
  - 证据来源：`api.github.com` 的 release 正文 + `D:\Strata\Strata-main\engine\BUILD.json`（`"version": "0.1.44.1"`, cuda 13.0, archs 75/86/89/120）+ live `strata.exe --help` + 引擎日志。

- **第 3 项 `--adapt-async 1` 实测中（2026-10-16 晚，老大「试第 3 项」）**：
  - 生效已证明（日志）：`adaptive tier asynchronous (--adapt-async 1): up to 160 swaps per round, a round every 1 windows (arena: copy-in only)`、`asynchronous adaptive tier: 1096 rounds, 29408 experts swapped in, 31.2 ms per round`。
  - **关键冲突（新发现）**：`STRATA_ADAPT_OVERLAP=1 is off: not with --adapt-async` → **这两个开关互斥**，开 async 就把今天下午采纳的 overlap 关掉。所以这是「二选一」不是「叠加」。
  - async 开着实测（本机 4k、concurrent 1、引擎 21:55 重启后）：`async-4k.json` 7 轮 decode 中位 **83.0**（79.8~87.1）、prefill 915.4、hit 63.8%；`async2-4k.json` 7 轮 decode 中位 **81.7**、hit 63.5%。**14 轮合并中位 82.4，hit 63.6%**。
  - async 关着（overlap=1）今天的对照：5 轮组 85.9 / 85.2（hit 68.3%）、3 轮组 80.4 / 81.3 / 82.2 / 80.3。**轮数不同不可直接比** → 已把配置改回 async 关（args 35→33，`--adapt-async` 已删，overlap 自动回来），等老大重启后跑**同样 7 轮 ×2** 再定案。
  - 弱点：官方那条 +4.2~5.2% 是在 **Q2_0**（比本机 IQ3_XXS 小得多、专家缓存压力完全不同）上测的，且官方说收益**全在代码/文档类提示词**、故事类持平；本基准用的是 filler 文本 = 故事类 → 本来就在「持平」那一档。另外 async 官方明说 `Not bit-exact run to run`。
  - **定案（老大 2026-10-16 晚：「关闭就行」）：`--adapt-async` 保持关闭**，配置里那两行已删（args 33）。理由：14 轮 vs 14 轮看着是 +5.2%（82.4 vs 78.3），但**同一配置今晚自己从 85.9 漂到 77.9（9%）**，漂移比要测的差还大；三次重启的引擎状态完全一样（专家缓存 1902/1892 槽、arena 锁 14564 MiB + 25 GiB、整块 cudaHostRegister 都失败）→ 差别不是配置造成的。要定论只能交替重启（开→关→开→关），老大决定不折腾。数据：`async-4k.json`、`async2-4k.json`、`noasync-4k.json`、`noasync2-4k.json`。
  - 附带事实：三次启动的日志都是 `cudaHostRegister of the whole arena FAILED (out of memory); 33 slices pinned (25 GiB)`，空闲物理内存约 4.8 GB（5,051,972 KB）→ **本机内存已经见底，任何更大的量化档都装不下**。

- **UD-Q4_K_XL（Unsloth 4-bit 档）判定：本机不换**（老大 2026-10-16 问「咋样」）。依据（`E:\Strata-bench\QUANTS.md` / `UNSLOTH_Q4.md`，0.1.44 版官方文档）：
  - 质量确实高一截：对 Q8_0 同 top-token **93.09%（KL 0.056）** vs 我们的 IQ3_XXS **84.46%（KL 0.202）**。
  - 但**内存装不下**：文件总大小 **111.3 GB**（我们现在 47.04 + 28.80 = 75.8 GB），路由专家 **71.7 GiB**（官方原话「约为 3-bit 模型的两倍」），PLE 表 IQ4_NL 26.8 GiB；官方「专家全进内存」规则要 **72 GiB 专家 + 16 GiB ≈ 88 GB 内存**，本机 64 GB 且现在空闲只剩 4.8 GB。
  - 速度本身也更慢：官方速度表（**注意测试环境：AMD R9700 32 GB、EPYC 8 通道 DDR4-2400 106 GB/s、专家全进内存**，不是本机）UD-Q4_K_XL 短故事 63-64 / 代码 85-88 tok/s，比 IQ3_S 的 75 / 95 慢。
  - 盘装得下：D 剩 311 GiB、E 剩 803 GiB → 111.3 GB 放得下，但没意义。
  - 顺带：`STRATA_HC_Q8=1`（第 2 项）只对 UD-* 文件有意义 —— 换到 UD-* 才有 Q8_0 超连接可读。
  - 唯一本机装得下的升级是 **IQ3_S**（官方新的 64 GB 默认档，87.7% 质量，官方 0.1.44.1 明说**比 IQ3_XXS 慢 10~15%、多用约 7 GB**）→ 与老大「要速度」相反，**不换**。

- **更新说明全文重读（2026-10-16 晚，老大「让你看更新不仔细就是一种不准」）—— 以此节为准，前两遍是带关键词过滤 + 截断读的，有错漏。** 原文已存成 `_r42.md / _r43.md / _r431.md / _r44.md / _r441.md`（下次要查直接读这些，别再抓 API）。

  - **① 最大的可疑项：overlap 在本机这一档卡上是官方点名的亏本项。** 0.1.43.1 原文：0.1.43 在 Linux NVIDIA 默认开 overlap 后，「**an RTX 5070 Ti desktop -21% (68.4 vs 86.4 tok/s with it off, the same build)**, an RTX 5060 Ti -19%, an RTX 5090 Laptop (WSL2) -21% (84.6 vs 106.6)。One RTX 5090 desktop gained 1-2%」→ 默认改回全平台关，并写「**measure it with your own A/B before you keep it**」。0.1.43 也写：Windows 上它一直是 opt-in，「since an RTX 5070 there decoded Q2_0 2.6% slower with it」。**我们配置里现在是开的**（`STRATA_ADAPT_OVERLAP=1`），今天下午那个「82.4→86.0」是跨重启比较，已被证明不可信。→ **下一步该测的是把它关掉**（本机是 5070 Ti Laptop，官方数据是 5070 Ti 桌面 -21%）。overlap 不改答案（官方：Answers are the same either way）。
  - **② 最值得试的新开关：`STRATA_ROUTE_RESIDENT`（opt-in，NVIDIA + AMD）。** 0.1.42：`STRATA_ROUTE_RESIDENT=0.5`「**RTX 5070 Q2_0 with a 22 GiB RAM budget +16.5% decode (5 of 5)**, KL 0.0085 mean on the 3060」——改答案。0.1.43：「The opt-in `STRATA_ROUTE_RESIDENT` runs one warp per token on NVIDIA and AMD: **+2% decode with a 32 GB cache, +6-8% with a 16 GB card's, same answers as before**」——=1 那档不改答案。本机 12G 卡、专家缓存只有 3.1 GiB（1902 槽），属于「小缓存」那一档。
  - **③ 官方自带基准工具（0.1.43 新增）：`BENCH.bat` / `./bench.sh`（`python tools/strata_bench.py`）**，3~10 分钟跑固定套件（短聊天、4K/16K 提示词、五轮 agent 会话、`--clients N`、`--long`），写成社区基准格式报告，**`--compare` 能把两次运行并排比**。本机 `D:\Strata\Strata-main\tools\` 里**没有** `strata_bench.py`（本地源码树还是 0.1.41 的，只有 `calibrate.py`、`bench_eviction.py`、`needle_bench.py`）→ 要用得从仓库取。以后做 A/B 应该用它，别再用我手写的 `measure_parallel.py`。
  - **④ 纠正我上一遍的几处错/漏**：
    - 0.1.44 的 UD-Q4「decode x1.34-1.40、4K 提示词 x2.07」原文条件是「**UD-Q4 在 64 GB 机器上：旧的内存预算规则 vs 全部专家常驻**」→ 那个大收益正是「全部专家常驻」带来的，本机 12G 卡 + 64 GB 内存做不到，所以拿不到。
    - 0.1.44「Dense Q8_0 矩阵按块读一行 decode +2.8~3.8%」只写了 **RDNA4 和 sm_86**，本机是 sm_120 → 不适用。
    - 0.1.44 原文 `STRATA_PCIE_MIN1=1`「**did not help on this card**」→ 别测。
    - 0.1.44 原文：`--adapt-async` 的答案差异是「**deterministic run to run, not equal to it**（跟阻塞版不同，但同一配置每次跑是一致的）」；而 `--help` 写的是「Not bit-exact run to run」——**两处说法不一致**，我上一遍照 help 说的「每次跑都不一致」说过头了。
    - 0.1.44 原文：**「Answers from the GSQ-RCO packs (Qwen, Swift, Coder) are byte-identical to 0.1.43.1」** —— 我们的模型正是 GSQ-RCO 包，所以 0.1.43.1→0.1.44 默认改动不碰我们的答案。
    - 0.1.44 原文：`STRATA_ROUTE_TAIL_SKIP=0` 只在「全部专家常驻」时才关；「**the RAM-budget mode keeps the skip (+26-67% there)**」→ 本机正是 RAM-budget/arena 模式，这个 +26~67% 已经在吃（日志 `route tail skip: 171851 missed experts skipped`）。
    - 0.1.43 的「Windows 下 GGUF 就地并行读专家」修复就是在 **RTX 5070 (Windows, Ryzen 5 7600, 64 GB) + IQ3_XXS** 上测的（常驻 22 GiB：故事 18.9→25.5、代码 13.5→21.1；常驻 12 GiB：1.67~1.85x）→ 本机常驻 43.8 GiB，比那两个场景宽裕，但这条修复已生效（日志 `expert arena read unbuffered`）。
    - 0.1.42 原文：RTX 5070 (Windows) Q2_0 上 tail skip 给 **77.0→85.6 tok/s (+11.2%, 3/3)**。
    - 0.1.42 还有「`--calibrate` 会把测出来的 pcie 份额写进配置」；本机 `tools\calibrate.py` 存在。
    - 0.1.42 的 `"prevent_sleep": true`（Windows 请求期间不睡眠）—— 笔记本上值得开。
    - 0.1.44 有个预览版生图接口 `POST /v1/images/generations`（默认关，setup 不提供）。
    - 0.1.44.1：重跑 setup 现在会保留你已装的档位（0.1.44 曾会把你换成 IQ3_S）；已被换过可用 `START-HERE.bat --setup --model IQ3_XXS` 换回来。
  - **⑤ 本机日志实测（最后一次启动 22:07:27 之后）**：`PLE direct read probe: 120028 rows/s (fine)`（远高于官方 15,000 rows/s 的门槛 → 0.1.43.1 那串 mmap 卡死问题本机不会遇到）；`Windows commit: 15.6 GiB left of a 83.7 GiB limit (RAM + page file)`；tail skip 在跑。
  - **⑥ 确认没有更新的版本**：release 列表 30 条，最新 `v0.1.44.1`（2026-10-14），往前依次 44 / 43.1 / 43 / 42 / 41 / 40.4 …，无 draft、无 prerelease。

- **overlap 关掉实测（2026-10-16 晚 22:37 重启后，老大「可以测」）—— 结论：关掉更好，配置保持 `STRATA_ADAPT_OVERLAP=0`。**
  - 生效证据（引擎日志 22:37:26 启动）：`adaptive overlap: off (STRATA_ADAPT_OVERLAP=1 turns it on)` —— 不是「看起来一样」，是日志明确说关了。
  - 关（`nooverlap-4k.json` 22:42 / `nooverlap2-4k.json` 22:45，各 7 轮）：decode 中位 **80.8 / 84.5**，14 轮合并中位 **81.0**、均值 81.8、最高 85.2；prefill **923.1**；hit 64.5%。
  - 开（`noasync-4k.json` 22:10 / `noasync2-4k.json` 22:13，各 7 轮，同配置同档位）：decode 中位 **77.9 / 79.1**，14 轮合并中位 **78.3**、均值 78.7、最高 82.7；prefill **923.0**；hit 65.0%。
  - **逐批对照 2/2 支持关**：80.8 vs 77.9（+3.7%）、84.5 vs 79.1（+6.8%）；14 轮中位 +2.7（+3.4%）、均值 +3.1（+4.0%）。prefill 两边一样（923.0 vs 923.1）→ 与官方「overlap 只影响 decode、答案不变」一致。
  - **偏差方向对「关」不利，所以 +3~7% 是下限**：今天同配置漂移是往下走的（85.9 → 77.9），「关」是更晚测的那一组。官方在 5070 Ti 桌面上报的是 -21%，本机只测到 +3~7%（Laptop vs 桌面、Q2_0 vs IQ3_XXS，环境不同，别把 -21% 当本机数字）。
  - **撤回方法**：把 `D:\Strata\Strata-main\strata-iq3_xxs.json` 里 `"STRATA_ADAPT_OVERLAP": "0"` 改回 `"1"`，重启引擎（`D:/Strata/stop-strata.bat` → `D:/Strata/Strata-main/START-HERE.bat`）。
  - 现在正式配置的两个 env：`STRATA_ADAPT_OVERLAP=0`（采纳：关掉更快）、`STRATA_NO_LARGEPAGES=1`（大页已否决，别再去试）。`--adapt-async` 保持不加（与 overlap 互斥，且本机看不出收益）。

- **`STRATA_ROUTE_RESIDENT=1`：采纳，已写进正式配置（2026-10-16 晚 23:49 定案）—— 本机目前最大的一项提速。**
  - 生效证据 + 幅度（**三组同配置、同重启方式，只改这一个开关**；4k、concurrent 1、每文件 3 轮）：
    - 关（`rr3-off-4k.json`，23:34:55 重启）：decode 79.4 / 83.2 / 82.9（中位 **82.9**），hit 61.1 / 65.4 / 65.0%
    - 开（`rr1-4k.json` 22:56 重启后）：92.1 / 100.7 / 103.0（中位 **100.7**），hit 70.6 / 79.1 / 79.7%
    - 开（`rr2-4k.json` 同一次启动）：90.9 / 99.4 / 102.0（中位 **99.4**），hit 70.8 / 78.8 / 80.2%
    - 开（`rr4-on-4k.json`，23:49 重启后）：87.9 / 98.0 / 97.7（中位 **97.7**），hit 71.9 / 79.6 / 79.8%
    - 更早的 14 轮基线（overlap 关、resident 关）：中位 81.0，hit 63~67%
  - **结论：decode +20~23%（81~83 → 98~101），命中率 65% → 79~80%，prefill 不变（922~924）。** 比官方写的「16G 小卡 +6~8%」大得多，但方向一致（本机 12G 卡、专家缓存只有 3.11 GiB / 1890 槽，属于官方说的「小缓存」受益档）。
  - **已排除的干扰**：专家缓存槽没变（1890 slots / 3.11 GiB vs 之前 1892、1902）；`data\expert-profile.bin` 修改时间仍是当天 03:25:38（基准没改写它）；prefill 完全不动。
  - **答案变不变：测不出结论，别当成「已确认不变」。** 固定问题（temperature 0、max_tokens 700，抓 reasoning_content+content）：关 `ans_off.txt` 460 字 sha1 8d46685cc7df；开 `ans_on.txt` 608 字 c57f586516be；**但同一状态内连问两次也不同**（`ans_on2.txt` 522 字 3b7dff1354c6）→ **本机这套配置（`--adapt-every 1 --adapt-swaps 160` + `STRATA_ROUTE_TAIL_SKIP=7`）本来就不是逐次逐字一致的**，所以「开/关答案不同」不能归因给这个开关。官方 0.1.43 原文说 `=1`「same answers as before」、0.1.42 说 `=0.5` 才改答案（KL 0.0085）。
  - 内存代价：进程私有内存 55.9~56.4 GB，`Windows commit: 14.9 GiB left of a 83.7 GiB limit`（之前 15.6 GiB）→ 多占约 0.7 GiB，本机还够用但更紧。
  - 撤回：把 `"STRATA_ROUTE_RESIDENT": "1"` 改成 `"0"` 或删掉，重启引擎。
  - 附带发现：每批内部第 1 轮总是偏低（88~92），第 2、3 轮才到 98~103 → 自适应层要热身，**以后 A/B 至少跑 3 轮，别拿第 1 轮比**。
  - 现在正式配置 env 三项：`STRATA_ADAPT_OVERLAP=0`、`STRATA_NO_LARGEPAGES=1`、`STRATA_ROUTE_RESIDENT=1`。

- **UD-Q4_K_XL 可能性复核（2026-10-16 晚，老大「看看 q4 的可能性」）—— 结论：本机不换，而且不是差一点。**
  - **本机新实测**：可见内存 61.7 GB，引擎在跑时**空闲只剩 4.5 GB**；D 盘顺序读实测 **1.70~2.06 GiB/s**（读 2~3 GB，冷区 1.70 / 1.76）；盘空闲 C 157 / D 312 / E 804 GB；内存是 **2 槽 DDR5-5600、2×32 GB，SMBIOS 报最大支持 256 GB**（物理上可升级）。
  - **官方硬数据**（`QUANTS.md` 表）：每生成 1 个 token 要读的专家数据 = **UD-IQ4_XS 1.16 GB / UD-Q4_K_XL 1.50 GB**（10 专家 × 48 层）；专家总量 55.4 / 71.7 GiB；PLE 表 26.8 GiB。
  - **官方最接近本机的一台机器**（QUANTS.md 第 134 行）：RTX A4000 16 GB + 62 GB 内存，UD-Q4_K_XL，**39 GiB 专家常驻内存**、其余走 NVMe（2.1 GB/s）→ **decode 14-20 tok/s、4K 提示词 134-144 tok/s，被 SSD 卡死**（llama.cpp 同机同文件 14.8-16.5 / 117-123）。本机现在是 **98~101 / 924** → 换过去等于 **5~7 倍慢**。
  - **本机连那个 39 GiB 常驻都做不到**：空闲 4.5 GB。粗算：1.50 GB/token ÷ 1.75 GiB/s = 0.86 s/token → 全靠 SSD 只有 ~1.2 tok/s；必须靠常驻才够。
  - **质量收益还会被吃掉一截**：本机开着 `STRATA_ROUTE_TAIL_SKIP=7`，官方实测 UD-Q4 的 KL 在「内存预算模式」（A4000、1500 GPU 槽）从 **0.053 涨到 0.115**（跳专家对大文件代价更大）。
  - **就算内存够也不等于更快**：官方 R9700（106 GB/s、专家全常驻）UD-Q4 短故事 63-64 / 代码 85-88 tok/s，比 IQ3_S 的 75 / 95 慢 → 加内存买的是质量（93.09% vs 84.46% 同 top-token），不是速度。
  - **唯一可行的路径**（如果老大以后想试）：内存升到 96~128 GB（本机 2 槽、支持 256 GB）+ 下载 111.3 GB（D 盘 312 GB 空闲够，hf-mirror 通）→ 预计速度仍比现在低 20~35%。现在别做。

- **IQ3_S 判定（2026-10-17 凌晨，老大「q3s咋样」）：不换。**
  - 官方 0.1.44.1 原话（`_r441.md` 第 9 行）：IQ3_S「**about 10-15% slower than IQ3_XXS, and about 7 GB more RAM**」；0.1.44 把它设为 **64 GB 机器的新默认档**。质量：87.69% / KL 0.144 vs 本机 IQ3_XXS 84.46% / KL 0.202（`QUANTS.md` 79/80 行）。
  - 本机两道障碍：① 内存 +7 GB，而引擎跑着时空闲只剩 4.5 GB；② **更硬的是显存** —— 启动日志 `expert cache auto: 5.19 GiB free, 700 MiB reserved -> 1993 slots`，接着 `only 0 MiB free once the slots are written (reserve 700 MiB); shrinking the expert cache` → 现在就已经在缩缓存，IQ3_S 的专家更大 → 能常驻的槽更少 → 命中率下降 → 实际速度损失会比官方那 10-15% 更大。
  - 顺带：KV 不是可以腾出内存的地方 —— 日志 `KV streaming: 32768 of 262144 cells per QSA layer in VRAM, the K/V in 3.09 GiB of pinned RAM`（总共才 3.09 GiB）。

- **`STRATA_ROUTE_RESIDENT=1` 的机制与代价（2026-10-17 凌晨查清，必须知道）**
  - **机制确认（日志原文，不是推测）**：`route-resident: margin=1 ranks=6-9 windows T<=8 (decode): tail_nonres=1748589 swaps=1551001 (88.7%) nonres_entries before=3916740 after=2365739` → 它把 decode 窗口的「非常驻条目」从 3,916,740 压到 2,365,739（**-40%**），swap 155 万次 → 这就是命中率 65% → 79% 的来源。
  - **代价：显存更紧，引擎自己报警。** 「VRAM free with everything loaded」：开 = **195 / 147 / 148 MiB**（带 `LOW: requests may stall` 警告 + `WARNING: only 148 MiB ... the driver can page GPU memory to system RAM`）；关 = **288 MiB**；今晚之前各次启动 287~294 MiB。→ 这个开关多吃 **约 140~150 MiB 显存**。
  - 引擎给的建议原文：`add --vram-reserve-mib 1064 to the config's args (or lower --max-context)`（现在配置里是 700）。
  - 待观察：00:10:03 日志又出现一次 `engine started`，前面没有崩溃/退出记录（老大是否手动重启待确认）。

- **当前配置的速度实测（2026-10-17 00:4x，overlap 关 + ROUTE_RESIDENT 开，引擎 00:10:03 启动）**
  - 4k 提示词（`sp1-4k.json` / `sp2-4k.json`，各 3 轮）：decode **94.5 / 94.2 / 103.0 / 93.8 / 103.9 / 98.8**（两批中位 94.5、98.8），prefill 939.9~954.0，命中率 70.8~80.6%
  - 短对话（`sp3-short.json`，300 token 提示词）：decode **97.4 / 102.5 / 109.2**（中位 102.5），**端到端 71.7 tok/s**（含读提示词与全部开销，这才是日常感觉到的速度），命中率 71.4~78.0%
  - 对比今晚开关前的基线 81~83 → 现在 94~104。6 轮跨度 93.8~103.9（10.8%）与已知同配置漂移（9%）一致 → **+20% 这个结论仍站得住（远大于噪声）**。
  - GPU 确实在算：`nvidia-smi` 显存 **11646~11705 / 12227 MiB（95% 满）**，64~67 °C。
  - **警告仍在**（按复盘规矩查的）：`154 / 122 / 0 MiB of VRAM free`、`shrinking the expert cache` → 显存 95% 满就是这个配置的常态，引擎说「可能 stall」，目前实测没卡过。
  - **没测的**：短对话没有「开关关掉」的对照 → 不能说短对话也 +20%，只能说它命中率同样高（71~78%）。

- **思考强度对能力的影响（2026-10-17 实测，规格 `SPEC-thinking.md`，脚本 `think_test.py`，结果 `think-results.jsonl`）**
  - 环境：本机 5070 Ti Laptop 12G / IQ3_XXS / 引擎 0.1.44.1（00:10:03 启动，overlap 关 + ROUTE_RESIDENT 开）/ temperature 0 / 单请求串行 / 12 题 × 2 次 × 5 档 = 120 次请求，全部跑完。
  - 五档：`reasoning_effort` = none / low / medium / high / high+`reasoning_budget_tokens:0`（不封顶）。配置里的封顶是 2000。
  - 正确率（/24）：**none 20、low 18、medium 18、high 20、high不封顶 20**。
  - **漂移 = 0**：五档共 60 个「同题两次」组合，没有任何一题两次判法不同 → 本套题的噪声底是 0，2 题的差算真实差异（但只有这 12 题，不外推）。
  - 中位耗时 / 平均思考长度：none **0.36s / 0 字**、low 1.56s / 232 字、medium 1.40s / 355 字、high 1.77s / 346 字、high不封顶 1.59s / 382 字 → **low/medium/high 中位耗时几乎一样**（官方说的「简单题三档都短想」本机成立）；none 比思考档快约 1.2 秒/题。
  - 按题看（关键）：
    - q3（加7乘3减6逆运算，要 5）：**只有 none 两次都错**，四档思考全对 → 多步算术必须思考。
    - q8（陷阱题「100 台机器 100 个零件」，正解 5）：**none 两次都对，low/medium/high 全错** → 想多了反而被「100 台」带跑。
    - q4（两骰子和为 7 = 1/6）：none 对、low/medium 错、high 对（none 反而烧了 299~367 token）。
    - q7（3,3,7,7 凑 24）：**五档全错** → 换思考档救不了，属于模型跟随能力问题（同「换量化档修不了模型不听话」）。
  - **封顶 2000 没起作用**：high 封顶 vs 不封顶，正确率与错题完全相同（都 20/24、都错 q7+q8），最大思考长度 1254 vs 1938 字符，最大 completion 643 vs 886 token → 这 12 题里从没碰到 2000 上限，**封顶不用改**。
  - 结论/建议：**默认 high 保持不动**（与 none 正确率相同，但 none 靠记忆答题，遇到没见过的多步题就错；high 只慢 1.2 秒/题）。要「秒回」的场景（界面即答、闲聊）可用 none。
  - 没测的：没测长上下文/长回答下的思考强度；没测并发；每档只有 24 次样本，2 题的差是真实的但样本小。

- **老大 2026-10-17 明确要求：还是要试 IQ3_S 和 UD-Q4_K_XL（推翻上面「不换」的推荐）。已开干 IQ3_S**
  - 实测下载速度（hf-mirror，157.29 MB / 18.24 s，HTTP 206）= **8.62 MB/s** → IQ3_S 83.6 GB ≈ **2.7 小时**，UD-Q4_K_XL 111.3 GB ≈ 3.6 小时。
  - 官方仓库 `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`：IQ3_S = 54.82 + 28.80 = **83.6 GB**；IQ3_XXS = 47.04 + 28.80 = **75.8 GB** → 差 **7.8 GB**（跟官方「约 7 GB more RAM」对上）。同一个仓库还有 IQ2_XS 68.0 GB、Q2_0 66.2 GB。
  - 官方原话（`_r441.md` 第 9 行）：IQ3_S「**about 10-15% slower than IQ3_XXS, and about 7 GB more RAM**」；回退命令官方给了：`START-HERE.bat --setup --model IQ3_XXS`。
  - 官方原话（`_r44.md` 第 42 行）：IQ3_S 是 **64 GB 机器的默认档**（取代 IQ3_XXS）→ 本机 61.7 GB 可见，正好在这一档的设计范围内。
  - 本机内存实测（引擎正在跑时）：空闲物理内存 **5.81 GB**；`strata` 进程 **WorkingSet 42.51 GB / Private 56.16 GB**，`strata-vision` 0.64 GB → 停掉引擎大约能腾出 42~48 GB。
  - **下载已在后台跑**：目标 `D:\strata\Strata-data\models\IQ3_S\`（D 盘空闲 312 GB），文件名与 IQ3_XXS 同规则，`curl -L -C -` 可断点续传。**回退 = 删这个文件夹**，现有 IQ3_XXS 一个字节不动。
  - **不用全下（老大 2026-10-17 问到，实测确认）**：官方仓库里 IQ2_XS / IQ3_S / IQ3_XXS / Q2_0 的 **shard 00002 是同一个文件**，SHA-256 全是 `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`（28.80 GB）。本机已有的 IQ3_XXS shard2 实测 SHA-256 **完全相同** → 已用 **NTFS 硬链接**放进 IQ3_S 目录（link count = 2，不占额外磁盘），并补了 `.done` 标记（内容就是一个时间戳，16 字节）。→ **只需下 shard 00001 = 54.82 GB**，省 28.80 GB ≈ 55 分钟。硬链接两边独立：删任一边名字，另一边数据还在。
  - **已取消（老大 2026-10-17 说「不用试了」）**：后台下载已停，`D:\strata\Strata-data\models\IQ3_S\` 整个删掉（里面只有 1.98 GB 半成品 + 硬链接 + 标记；硬链接删掉不影响 IQ3_XXS）。删完实测：IQ3_XXS 两个文件完好（47,039,860,096 + 28,800,138,432 字节），D 盘空闲 311.7 GB。**IQ3_S 从没试跑过，没有任何速度数据。** 上面这些数字（8.62 MB/s、shard2 逐字节共享、+7.8 GB 内存、官方「10-15% 慢」）是查证来的，以后要再试直接接着做，别重测。
  - **UD-Q4_K_XL：老大 2026-10-17 明确说「不要 q4」→ 已否决，不要再下载、不要再提。** 留档的理由：routed experts **71.7 GiB**、每 token 要读 **1.50 GB**，本机装不下 → 走 SSD；官方 `_r43.md` 第 25 行低内存实测「**a low-memory setup decoded at 2.6 tok/s**」（0.1.43 修成并行读后也就个位数到十几 tok/s）→ 比现在 94~104 慢一个数量级。真要让 Q4 可用只有一条路：**加内存**（本机 2 槽 DDR5-5600，最大支持 256 GB）。

- **预填充为什么不到 1000（2026-10-17 实测，不是猜）**
  - 长度扫描（`pf-1024/4096/16384/65536.json`，各 2 轮）：1k **341.9**、4k **908.2**、16k **908.0**、64k **968.1** tok/s（decode 100~102，命中率 78.7~78.9%）→ **4k 以上完全平**，说明 900~970 是稳态上限，不是固定开销；1k 低是因为固定开销占比大。另一次独立实测：32,051 token / 33.5 s = **958 tok/s**。
  - 预填充期间 `nvidia-smi` 采样 72 次：**GPU 占用 98~100%**，但**显存控制器占用只有 20~33%**，显存 **11,565 MiB**，**功耗 93~115 W**，SM 时钟 **2610~2692 MHz**（这张卡最高 3090 MHz）→ **不是显存带宽卡住**，是算力/内核调度 + 功耗墙（笔记本 5070 Ti 被压在 ~115 W，频率拿不到 3090）。
  - 结构原因（官方 `DETAILS.md` 第 1550-1551 行原话）：「Prompts are processed in chunks of up to 8,192 tokens (`--prefill auto`; 32,768 opt-in) **with the experts streamed to the GPU over PCIe**」→ MoE 预填充每个 token 也要碰 10 个专家 × 48 层，本机显存 11.57/12.23 GB 已满，专家要靠 PCIe 从内存搬（命中率 78.9%）。
  - 参照（官方数字，不是本机）：R9700 32 GB + 专家全在内存，IQ3_S 32K 提示词 **1,555 tok/s**；同卡 llama.cpp UD-Q4 4K 只有 198-257。本机 968 属于正常偏好。
  - **唯一有官方实测的提速开关**：`--prefill auto:32768`（AMD 上 74K 提示词 +23%）；官方在 **RTX 5070** 上测 ring 相关：32K 提示词 **+18.5% / +9%**（两种内存状态），**4K 提示词不变（-0.7%~+1.1%，逐位相同）** → 只对长提示词有意义，而且本机显存已 95% 满、引擎已报 LOW-VRAM → **推荐不动**（要动就得重启，老大双击）。

## 怎么运行
- 重跑对比：`python E:\Strata-bench\bench_new.py`（中途助手会下线约 2 分钟）
- 单独测某个端口：`python measure_parallel.py --host http://127.0.0.1:8080 --tier 4k --tokens 4096 --concurrent 1 --runs 3 --log <引擎日志> --out x.json`

---

# 10. 升级引擎 0.1.44.1 → 0.1.45（2026-10-18，源码已就位，等老大双击 bat 换引擎）

## 为什么升
- 老大想找 **Qwen3.8-Flash-Next 无审核版 IQ3_XXS**。结论：**有**，在 HuggingFace `orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF`（hf-mirror 可下），IQ3_XXS 两个分片 41.57 + 37.78 = **79.35 GB**，另 MTP 草稿 3.85 GB。
- 它是 **abliteration**（把「拒绝方向」从权重里正交化掉），不是挂名。作者自测：有害提示拒绝率 64–100% → **~0–3.3%**，能力 ±2 分内（MMLU-Pro / GSM8K / CMMLU 类）。**这些数字是作者自己测的，本机未验证。**
- **关键卡点**：`0.1.44` 起引擎**拒绝加载**这个模型（报 `compress_ratios[3] = 0, but full_attention_interval = 4`，issue #2396）→ **0.1.45（2026-10-17 发布）修好了**。本机是 0.1.44.1 → 必须先升级。
- 官方说明：0.1.45 对 Flash-Next 系列回答**与 0.1.44.1 逐字节相同**（官方 identity 测试，不是本机实测）。

## 已经做完的（都跑过、有输出）
1. **下载并校验**：`strata-windows-x64.zip` 165,243,142 字节，SHA256 `a1d4cafb…9f3b859e` **与官方 SHA256.txt 一致**（MATCH）。源码包 `v0.1.45` 23,208,999 字节（codeload 通）。
2. **参数兼容性已验证**：新引擎 `--help` 259 行；我们配置里 18 个参数逐个查过，`--vram-reserve-mib` / `--adapt-decay` 没写进 help 但**实测被接受**（对照：`--totally-bogus-arg` 会报 `unknown argument`）→ **现有 `strata-iq3_xxs.json` 不用改**。
3. **备份（可回退）**：
   - 源码 5279 个文件 → `backup-Strata-main-source-0.1.44.1.zip`（54 MB）
   - 旧引擎 4 个文件 → `engine-backup-0.1.44.1\`（318 MB）
   - 老大改过的 5 个界面文件 + 配置 → `E:\Desktop\aigz\strata-panel\web-backup-phase2-20261018\`
4. **源码已覆盖成 0.1.45**：解压 3286 个文件到 `D:\Strata\Strata-main`，**0 错误**；`requirements.txt` 与 0.1.44.1 **完全相同** → 不需要装新 Python 包；配置文件没被动。
5. **bat 已写好**：`D:\Strata\Strata-main\升级引擎0.1.45.bat`（GBK 存、中文提示）= 停引擎 → 换 4 个引擎文件 → 启动。

## 下一步（只能老大做）
- **双击 `D:\Strata\Strata-main\升级引擎0.1.45.bat`**（引擎文件正在被占用，助手不能自己换 = 会把自己关掉）。
- 起来之后助手验收：读 `/metrics` 或引擎日志确认版本 0.1.45、`--kv-resident` / `ROUTE_RESIDENT` 等开关还在、tok/s 与升级前对比。

## 踩过的坑 / 别再试
- **release 的 zip 里只有引擎 3 个可执行文件**（`strata.exe` / `strata-vision.exe` / `strata_kq.dll` / `BUILD.json`），**没有界面和脚本** → 界面/脚本要从**源码包**（codeload 的 tag zip）取。
- **`UPDATE.bat` 在这台机器上不能升到新版本**：`D:\Strata\Strata-main` **不是 git clone**（没有 `.git`），它会打印「不能自己取新文件」然后只跑 `--update`（重查当前版本的引擎）→ 升不到 0.1.45。
- **单独跑 `strata.exe --help` 会报缺 `cublas64_13.dll`** → 先把 `D:\Strata\Strata-main\.venv\Lib\site-packages\nvidia\cu13\bin\x86_64` 加进 PATH（配置的 `lib_dirs` 就是它）。
- **0.1.45 的上游界面也改了**（`index.html` 15372→16960、`monitor.js` 8418→8410），所以**现在用的是官方原版界面**，老大那 5 个改动文件**还没移植** → 移植是另一个活，要在 0.1.45 的界面上重做，不能直接覆盖回去。
- `serve\web\nul` 是个 56 KB 的怪文件（Windows 保留设备名，zip 备份时被跳过）→ 要删得用 `\\?\` 前缀的路径。
- 下载速度实测 **~170–250 KB/s**（objects.githubusercontent.com），157 MB 约 11 分钟 → 大文件用 `curl -C -` 断点续传 + 后台跑。

## 还没做的（等老大点头）
- 下载无审核版 79.35 GB + 跑 `tools/iq_pack.py --compat-bf16` 打包 + 写 `strata-orca-iq3_xxs.json`。
- 移植 strata-panel 的界面改动到 0.1.45。
- 参考文档已存本地：`docs-from-github\strata_MODELS.md`、`docs-from-github\strata_ORCA.md`（ORCA 全文含配置示例）。

## 10.1 0.1.45 升完后的速度实测（2026-10-18 01:0x，同脚本同配置）

脚本：`measure_parallel.py --tier 4k --tokens 4096 --concurrent 1 --runs 3`（两轮 4k：`ab45-a.json` / `ab45-b.json`；短提示词：`ab45-short.json`）

| 项 | 0.1.45（今天） | 0.1.44.1（2026-10-17 基线） | 差 |
|---|---|---|---|
| 4k decode 中位 | **89.3 / 96.4** | 94.5 / 98.8 | -5.5% / -2.4% |
| 短对话 decode 中位 | **95.8** | 102.5 | -6.5% |
| 短对话端到端 | **66.5** | 71.7 | -7.2% |
| 专家命中率 | 72.6~78.8% | 70.8~80.6% | 基本相同 |

- **本机今天自己的漂移**：同一个 0.1.45、同配置、两批 4k 中位差 **7.4%**（89.3 vs 96.4）→ 上面所有差异（2.4~7.2%）**都小于等于本机噪声** → **结论：没有证据表明 0.1.45 变慢**（也不能证明完全相同）。
- **这是跨天 + 跨重启的比较**（`knowledge/bench-ab-and-docs.md` 明说这种比较不算硬证据）→ 要硬证据只能换回 0.1.44.1 做同场交错 A/B（需要老大再双击两次 bat）。
- 配置与开关确认未变：`/metrics` = version 0.1.45、`max_context 262144`、`kv int8`、`kv_resident 32768`、`spec_min_p 0.70`、`arena 40925 MiB`、专家槽 1798；日志 `adaptive overlap: off`、`R4 hit path ON / 1798 resident experts`。
- 0.1.45 新行为：启动实测 `PCIe probe: 14.4 GB/s -> pcie_frac 0.40 (default 0.55)`，运行中又重算成 `0.15`。以前固定 0.40。

## 10.2 无审核版模型下载被卡（2026-10-18 实测）

- **`orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF` 是 gated（受限）模型**：hf-mirror 下载返回 **403**，原文 `Access to model ... is restricted and you are not in the authorized list.` → 要 HF 账号 + 作者批准。文件列表 API 能看，文件下载不行。
- 本机 `huggingface.co` 实测 **不通**（`curl` 返回 000）→ 老大没法在本机注册/申请。
- 备选实测：**ModelScope 没有**（`api/v1/models/orcarouter/...` → 404 record not found）；**Ollama 有该模型但只有大档**（页面显示 174 / 205 / 221 GB，无 iq3_xxs，`/v2/.../manifests/iq3_xxs` → 404）。
- **速度实测**（决定 79 GB 可行性）：hf-mirror 公共大文件 range 下载 **5.08 MB/s**（16 MB / 3.3 s）→ 79.35 GB 约 **4.3 小时**；GitHub releases 只有 **170~250 KB/s**（157 MB 用了 11 分钟）→ 走 GitHub 下 79 GB 要几天，不可行。
- **下一步要老大做的**：在能上网的设备/手机上开 `huggingface.co` 注册账号 + 对该模型点申请访问 + 生成 access token，之后助手再测 hf-mirror 带 token 能否下载。

## 10.3 不用申请也能下的无审核版（2026-10-18 实测，hf-mirror 都返回 206）

| 源（HF 仓库名） | 档 | 体积 | 实测可下 | 备注 |
|---|---|---|---|---|
| **`SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF`** | **IQ3_XXS** | **44.09 + 26.82 = 70.91 GB** | 206，2.05 MB/s | **最对口：跟本机现有模型同族（GSQ-RCO）同档（IQ3_XXS）**；作者有 `strata/README.md` 专用说明 |
| `jimmy31chen/RVN-...-IQ3_S-Strata` | IQ3_S | 82.78 GB（单文件 + 现成 pack） | 206，0.77 MB/s | 已用 `iq_pack.py --compat-bf16` 打包好，29 万下载 |
| `0bserverx/RVN-...-Uncensored-GGUF` | IQ3_XS / IQ3_S / IQ3_M / Q2_K…Q6_K | 74.9~156 GB | 206，1.16 MB/s | 8 分片，跨 shard 切开 → 直接打包会失败，要先 merge |
| `mradermacher/Qwen3.8-Flash-Next-Uncensored-GGUF` (+`-i1-GGUF`) | Q3_K_S…IQ4_XS | 82.7~91.7 GB | 206，0.41 MB/s | 没有 IQ3_XXS |
| `DavidAU/...-Turbo-Brilliance-50x-...` | IQ3_S | 78.10 GB + mmproj | 206，0.79 MB/s | **不推荐**：卡里自己写灌了「15 个 AI CONSTRUCTS 人格」，说明浮夸（120B/180B 自相矛盾） |

- **官方 OrcaRouter 那份为什么下不了**：gated 403。hf-mirror 也不绕过受限仓库。
- **SC117 用法（作者原文要点，摘自 `strata/README.md`）**：
  1. **必须用 `tools/iq_pack.py --gguf <shard1> --out packs/sc117_iq3_xxs` 重建 pack**，不能复用官方 GSQ-RCO 的 pack，否则报 `ArenaExpertSource: the pack's native_experts.txt does not match the model`。`iq_pack.py` 会自动找第二个分片。**不需要 `--compat-bf16`**（GSQ-RCO 本来就存 BF16 投影）。
  2. 配置改：`--pack` / `tokenizer` 指向新 pack，`--native` = shard1，`--ple-gguf` = shard2，`--mtp` 用它给的 `strata/rt`（或沿用本机现有 `mtp/rt`，两者都来自原版草稿头），`vision.model` 换 shard1、mmproj 可沿用。
  3. **它的 MTP 草稿头没有 abliterate**（作者明说：没有任何 abliterated MTP 头发布过）→ 草稿层还是原版行为。
  4. 保留官方 pack 目录以便切回。
- 速度实测（决定下载时长）：hf-mirror 公共文件 5.08 MB/s、这几个仓库 0.4~2.05 MB/s → 70.91 GB 约 **4~10 小时**，必须 `curl -C -` 断点续传后台跑。
- 官方申请入口（老大用别的设备开）：`https://huggingface.co/orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF`、token 页 `https://huggingface.co/settings/tokens`。

## 10.4 SC117 到底改了什么（摘自它的 `README.zh-CN.md`，全文存 `sc117_zh.md`）

- **底子** = `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`（**就是本机现在用的同族 GSQ-RCO**）；**消融权重来源** = `orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF`（**老大想要的那份官方无审核版，144 个张量字节直接搬过来**）→ 两条路在「消融」这件事上同源。
- 做法是 **GGUF→GGUF 字节级张量搬运**：135/144 直接搬字节；剩下 9 个本应 Q2_0 的专家张量，用 GSQ 自己学到的块尺度把消融值重编码成 Q2_0。**没有任何 dequantize→quantize 循环、没有从 BF16 重量化**（GSQ 学到的值与尺度一个比特都不重算）。
- **动了 144 个张量**（全文件 1223 个），全在「写回残差流」的投影上，覆盖 48 层（表是 IQ3_S 档）：`ssm_out` 36 个→Q8_0、`attn_output` 12 个→Q8_0、`ffn_down_shexp` 48 个→Q8_0、`ffn_down_exps` 48 个（类型不变、值换）。95 个类型改变，49 个保持官方类型。合计体积 +0.25 GB。
- **没动的**：`token_embd` 与 `output`（输出头）—— 很多消融会顺手处理输出头，这份没有 → 可能残留少量拒答。其余 1079 个张量逐字节未变。
- **四道校验**：① 张量名集合 1223=1223；② 同名张量反量化后相关度 0.992–0.996（布局对齐）；③ 1223 次逐张量 blake2b：**144 个目标全不同、1079 个非目标全相同（0 例外）**；④ 行为抽检只跑了一小组探针（作者自己说不能当全面评测）。
- 作者报的代价（**作者的机器，双卡 256K，不是本机**）：体积 +0.23 GiB、decode 104.5→104.4（−0.1%）、prefill 3086.9→3035.1（−1.7%）、专家槽 12185→12095、草稿接受率 66.5%→67.1%。
- **它的 MTP 草稿头没有 abliterate**（作者明说没有任何 abliterated MTP 头发布过）。

### 10.5 开始下载 SC117 无审核版 IQ3_XXS + 下载加速实测（2026-10-18）

- 老大指令：「下 SC117，但你可不可以加速」。
- **加速实测**（hf-mirror 同一文件，Range 段，15~25 秒窗口，只测吞吐不落盘）：
  | 连接方式 | 实测吞吐 |
  |---|---|
  | 单连接（三轮） | 8.38 / 9.27 / 8.86 MB/s |
  | 2 路（两个不同分片） | 4.64 MB/s |
  | 4 路（同一文件） | 2.99 MB/s |
  | 4 路（15 秒窗口） | 2.17 MB/s |
  | 8 路（15 秒窗口） | 0.84 MB/s |
  → **并行不加速，反而越开越慢**：hf-mirror 按 IP 限总带宽并有并发惩罚。**结论：脚本故意用单连接串行，这就是本机最快。**
- 对照：nodejs.org 单连接只有 0.90 MB/s（那个源本身慢，不是本机上限）；ModelScope 搜索 API 返回 `404 page not found`（没有更快的国内镜像）。
- 脚本：`E:\Desktop\aigz\strata-bench\dl-sc117\dl.sh`（`curl -L -C -` 串行两分片，断了自动续传重试，日志 `dl.log`）。
- **坑**：`--retry-conn-refused` 在本机 curl 8.19 (mingw32) 是 **unknown option**，直接 exit 2 —— 已删掉，别再往脚本里加。
- 落地目录：`D:\Strata\Strata-data\models\sc117_iq3_xxs\`。D 盘下载前空闲 434 GB，装 70.91 GiB 后约剩 363 GB。选 D 盘的理由：与现有模型同盘，读速本机实测 1.70~2.06 GiB/s（E 盘没测过）。
- 分片真实大小（服务端 Content-Range 确认）：shard1 = 47342144896 B，shard2 = 28800138432 B，合计 76142283328 B = 70.91 GiB。
- 运行中实测：curl 进程 1 个；30 秒增量 299 MB ≈ 9.0 MB/s；shard1 剩余 ETA ≈ 80 分钟，两分片总计 ≈ 2.2 小时。
- 给老大的工具（GBK 存，可双击）：`dl-sc117\看下载进度.bat`、`dl-sc117\继续下载.bat`（后者会先检查有没有 curl 在跑，防双开）。
- **撤回方法**：整个 `sc117_iq3_xxs` 目录删掉就回到原样 —— 现有模型、pack、配置这阶段一个都没动。
- 下一步（等下完才做）：`iq_pack.py --gguf <shard1> --out D:\Strata\Strata-data\packs\sc117_iq3_xxs`（**不加 `--compat-bf16`**）→ 改配置（`--pack` / `--native` / `--ple-gguf` / tokenizer / `--mtp`）→ 新旧模型各一个 bat 给老大双击。

### 10.6 关引擎前后的下载安排 + 三个新坑（2026-10-18 01:51）

- 老大要关引擎 → 下载已改成**独立进程**：`powershell Start-Process "C:\Program Files\Git\bin\bash.exe" dl.sh`。关掉引擎（8080）不影响它；`继续下载.bat` 同样不依赖引擎。
- **坑 1：不要编辑正在运行的脚本。** 我在 dl.sh 跑着的时候用 Edit 改了它，bash 是流式读脚本文件的，结果行为错乱（已删掉的 `--retry-conn-refused` 又出现在日志里、循环重复跑）。正确顺序：**先停 → 再改 → 再启动**。
- **坑 2：用 `CommandLine -like "*dl.sh*"` 找进程会匹配到「查询命令自己所在的 bash」**，`Stop-Process` 一执行就把我自己的 shell 杀了，表现为 `exit 255` 且没有任何输出。要查进程先只列 ProcessId / ParentProcessId / CreationDate，别直接按匹配串杀。
- **坑 3：两个 curl 同时 `-C -` 写同一个分片 → 文件不可信**（确实出现过 2 个 curl 进程）。已删掉重下，损失 5.76 GB ≈ 11 分钟。dl.sh 开头现在先检查有没有 curl 在跑，有就自己退出。
- 现状（1:51 实测）：1 个 curl 进程，独立窗口，30 秒增量 300941312 字节 ≈ 10 MB/s；日志换用 `dl-sc117\dl2.log`（旧 dl.log 里的记录作废，别再据此判断）。

### 10.7 对比测试工具已写好并自检通过（2026-10-18 10:45，目录 `abtest\`）

- 规格：`abtest\SPEC_abtest.md`（三关、题数、判据、通过线全部写死）。
- 已写好且**跑过自检**的脚本（都用 `D:\Strata\Strata-main\.venv\Scripts\python.exe` 跑）：
  - `check_tensors.py`：解析 GGUF 张量表 + 逐张量 blake2b。**自检方式：拿 `mtp-q2_0.gguf` 跟自己比 → 31/31 张量、0 差异、判据全过**；另 `--filehash` 能正确报 GGUF 版本 3 / 张量数。
  - `test_refusal.py`：30 道探针题 + 10 道正常题，并发 1、每题 2 遍，只判「有没有拒绝套话」、只留回答前 40 字（不外流有害内容）。强判据/弱判据分开算，避免把「提到风险」误判成拒答。
  - `test_ability.py`：40 题全自动判分（数学 15 / 代码 7 / 中文 8 / 指令跟随 5 / 长上下文 5），跑 3 轮算**本机噪声带**；只有均值差超过噪声带才允许说「能力变了」。代码题在临时目录跑、8 秒超时、**代码里出现 os/sys/eval/exec/open/subprocess 就直接判 0 分不执行**。
  - `selftest_ability.py`：**判分器自检 = 把理想答案喂给判分器，必须 40/40。实测 40/40 全绿。**
  - `switch_config.py`：改配置指向哪份模型，`--to sc117|official|--show`，改前自动备份 `strata-iq3_xxs.json.bak-<目标>-<时间>`。**防护已实测**：模型没下完时 `--to sc117` 直接退出码 2 报「文件没下完，不能切」，配置一个字节没动。
- 给老大的两个 bat（GBK 存，`abtest\`）：`切到无审核版.bat`、`切回原版.bat`（停引擎 → switch_config 检查+改配置 → 重启引擎）。**pack 没建好之前双击会被拒绝，不会把配置弄坏。**
- 第一关输入已齐：官方 shard1 47039860096 B、SC117 shard1 47342144896 B（+0.28 GiB）；shard2 两边都是 28800138432 B（**大小一模一样**，说明 PLE 表那一半没动）。第一关已在后台跑（10:44 起）。
- 下载状态：分片1 **完成**（10:40:57，47342144896/47342144896 校验通过）；分片2 进行中。每 20 分钟有一个 `sc117-watch` 定时任务自动检查/续传，两个分片都到目标字节后自动删除该任务。

- **10.7 补记的坑**：GGUF 元数据里的**数组**（tokenizer 那些）不能用 `struct.unpack('<I'*n)` 拼超长格式串 —— 本机实测报 `struct.error: bad char in struct format`。正解：`array.array(typecode).frombytes(...)`。修完官方 shard1 解析出 **1223 个张量 / 67 条元数据**，与作者卡片声明的 1223 一致。

### 10.8 第一关结果：本机实测复验通过（2026-10-18 11:0x）

命令：`check_tensors.py --a 官方IQ3_XXS shard1 --b SC117 shard1 --out 第一关_张量对比.json`
实测输出：

- 张量数 A/B：**1223 / 1223**，共同 1223，**不同 144，相同 1079**
- 差异按族：`ffn_down_exps 48 / ffn_down_shexp 48 / ssm_out 36 / attn_output 12` —— 与作者卡片声明的 48/48/36/12 **完全一致**
- 差异原因：**96 个「类型或尺寸不同」+ 48 个「内容不同」**（卡片在 IQ3_S 档说的是 95 变类型 / 49 保持原类型，档位不同数量略有差，结构一致）
- `token_embd.weight`、`output.weight`：**未变**（与卡片「没动输出头」一致）
- 整文件 blake2b：官方 `1b8f3f39…0088`，SC117 `b69d063f…71e9`（不同，符合预期）
- 判据 1、2、4 通过；判据 3 一开始报「不通过」是**我判据代码的 bug**（张量名都以 `.weight` 结尾，族名在倒数第二段），已修 `[-1]`→`[-2]`，从已存 JSON 重新统计：不在这 4 族的差异 = **0 个**。
- **结论：这份下载的东西确实是「只动 144 个张量的消融版」，不是挂名。** 第一关通过，可以继续第二、三关。

### 10.9 原版基线已测完（2026-10-18 11:2x，引擎 0.1.45、IQ3_XXS、并发 1、单题约 26.6 秒）

第二关 `原版_拒答.json`：
- 探针拒答率 **66.7%**（30 题 × 2 遍）；正常题误拒率 **0.0%**（没有过度拒绝）
- 按题看：**两遍都拒 18 题、一遍拒一遍不拒 4 题、两遍都不拒 8 题** —— 这版本来的对齐就不算强，有 8 类请求它本来就不拒
- 探针「疑似说教」56.7%，正常题 0.0%

第三关 `原版_能力.json`：
- 各轮得分 **[40, 39, 39]**，均值 **39.33/40**，**本机噪声带只有 1 分**
- 分类：数学 15/15、代码 7/7、指令跟随 5/5、长上下文 5/5、中文 7.33/8（错的是「得」的词性那题）
- 判据意义：**噪声带 1 分 → 无审核版若均值掉 ≥2 分就是真的下降**；反过来这套题对原版几乎满分（天花板效应），只能用来发现「变差」，不能用来证明「变强」。

### 10.10 两个分片下载完成 + 第一关五判据全通过（2026-10-18 11:29）

- 日志：`11:29:30 完成 ...00002-of-00002.gguf 28800138432/28800138432 字节 校验通过`、`=== 两个分片全部下载完成 ===`。curl 进程 0。
- shard2 整文件 blake2b 对比：官方与 SC117 **完全相同** `2149758973b8057b3c1c1ec7eb3e618b48974ce377c06092c212594a8240f63c`（两边都是 1 个张量 / 3 条元数据 = PLE 表那一半，逐字节没动）。
- 第一关五条判据（张量名一致 / 差异恰好 144 / 只在 4 族 / 输出头未变 / shard2 相同）**全部通过** → 下载的东西确认是真消融版。
- 自动检查任务 `sc117-watch` 已自行删除（`cron list` 返回 `No scheduled jobs`）。
- 实测速度回顾：单连接 9~10 MB/s 最快；2/4/8 路并行实测 4.64 / 3.0 / 0.84 MB/s 更慢 → 别再试并行。
- 下一步：老大双击 `stop-strata.bat` 关引擎 → 我建 pack（引擎关着跑，内存才够）→ 老大双击 `abtest\切到无审核版.bat` → 我跑第二、三关。

### 10.11 「切到无审核版.bat 运行不了」的原因 + bat 已改成一站式（2026-10-18 11:3x）

- 原因不是 bat 坏：`switch_config.py --to sc117` 实测报 `pack 还没建，不能切` 退出码 2 —— 防护按设计生效（配置一个字节没动）。
- 已把 `abtest\切到无审核版.bat` 改成**一次双击全做完**：停引擎 → 跑 `iq_pack.py --gguf <SC117 shard1> --out D:\Strata\Strata-data\packs\sc117_iq3_xxs`（**不加 `--compat-bf16`**，SC117 不需要）→ `switch_config.py --to sc117` → 启动引擎。
- **失败会自动兜底**：建 pack 失败或切换失败，bat 会用**原来的模型**重启 Strata，不会把他留在引擎关停状态。
- 注意：pack 那一步要读 44 GB，约 10~20 分钟，窗口别关；这期间引擎是关的（助手不在）。
- 待观察：配置里的 `--expert-profile D:\Strata\Strata-main\data\expert-profile.bin` 是配官方模型生成的，换成消融版（96 个专家升到 Q8_0）后引擎会不会报不匹配 —— 报了再说，作者卡片提过「复用旧 pack 会报 `native_experts.txt does not match the model`」，我们建的是新 pack 所以不该遇到。

### 10.12 「打开闪退」真因找到：bat 内容被 Python 转义吃掉（2026-10-18 11:4x，四个 bat 已重做）

- 第一个嫌疑：行尾。实测旧文件 `CRLF 个数: 0 / 裸 LF: 31 / 多行括号块: 2` → cmd 读到裸 LF 的多行 `if errorlevel 1 (` 会解析崩 → 窗口闪退。
- **真正的病根**：我用 Python **非 raw** 三引号字符串生成 bat，里面的 `\tools` 被当成 **TAB**、`\abtest` 里的 `\a` 被当成 **BEL 控制字符**，路径整个被吃掉：回读看到 `D:\Strata\Strata-main<tab>ools\iq_pack.py`、`E:\Desktopigz\strata-benchbtest\switch_config.py`（`\a` 把 `a` 吞了）。→ python 找不到脚本 → errorlevel 1 → 掉进括号块 → 闪退。
- 修法：bat 内容一律用 **raw 三引号 r"""..."""**（单反斜杠照抄），不用 `%s` 拼含反斜杠的字符串；写完自动查 `b'\t' \x07 \x0b \x0c` 是否出现在文件里。
- 重做后的实测（四个 bat）：`切到无审核版.bat 1597字节 CRLF=29 裸LF=0 括号块=0 控制字符=[]`、`切回原版.bat 939/21/0/0/[]`、`继续下载.bat 268/10/0/0/[]`、`看下载进度.bat 212/8/0/0/[]`。
- 回读逐行确认路径完整：`D:\Strata\Strata-main\tools\iq_pack.py`、`E:\Desktop\aigz\strata-bench\abtest\switch_config.py`、SC117 shard1 全名、`D:\Strata\Strata-data\packs\sc117_iq3_xxs`。
- 依赖已核实存在：`serve/server.py`(430671B)、`tools/iq_pack.py`(35755B，参数确有 `--gguf`/`--out`)、`.venv/Scripts/python.exe`；启动那行与官方 `run-iq3_xxs.bat` 完全一致。
- 现有 pack 结构（照此预期新建的）：`dense.bin 1.54GB / index.txt / native_experts.txt / tokenizer/ / conversions.json`；`iq_pack.py` 会自己导出 tokenizer（脚本第 604-606 行），不需要 `--base`。

### 10.13 已切到无审核版并在跑第二、三关（2026-10-18 11:5x）

- 一站式 bat 实测跑通：建 pack → 备份改配置 → 自动重启引擎。老大贴回的窗口输出全绿。
- **确认引擎真换了模型**（判据 = 引擎日志，不是嘴上说）：`engine started: ... --pack ...packs\sc117_iq3_xxs --native ...abliterated-IQ3_XXS-00001... --ple-gguf ...00002...`；`1466 MiB of weights loaded from ...packs\sc117_iq3_xxs`；`PLE on ... abliterated...00002`。
- 旧 `expert-profile.bin` **没报不匹配**：`profile ...: 24576 ranked pairs, built for 24576 slots` → 不用重新生成。
- 新 pack 与原版逐项对齐：`dense.bin 1538035200`（完全相同）、`index.txt 93699`（原版 93687，多的 12 字节 = 模型文件名变长）、`native_experts.txt 3309`（原版 3296）。
- **坑：bat 被双击了两次** → 有两个备份（`.bak-sc117-20261018-114831` / `-115137`）、引擎起了两次（11:51:01 / 11:52:14）、pack 建了两遍。结果没坏，但 **告诉老大只双击一次**；两个 iq_pack 并发写同一个 `dense.bin.tmp` 理论上有写坏的风险。
- 新现象要盯：引擎报 `WARNING: only 50 MiB of VRAM free at the start of this request (below 1024 MiB)`，建议 `--vram-reserve-mib 1728`。消融版把 96 个专家升到 Q8_0，显存比原版更紧 → 第三关的速度数字要留意是否被这个拖慢。
- 正在跑（后台）：`test_refusal.py --reps 2 --out 无审核版_拒答.json` → `test_ability.py --runs 3 --out 无审核版_能力.json`，约 90 分钟。跑完跟原版基线（拒答 66.7%、能力均值 39.33、噪声带 1）对比出三张表写 `RESULT.md`。
- 撤回：双击 `abtest\切回原版.bat`（会自动备份再改回）。

### 10.14 二、三关跑完：结论 = 审核拆掉了、能力没掉（2026-10-18 12:1x，全部数字在 RESULT.md）

- 第二关：**探针拒答 66.7% → 1.7%**（144 次里只 1 次被判拒答，查原文是正经回答被正则误伤，真实≈0）；正常题误拒两版都是 0.0%；疑似说教 56.7% → 35.0%。判据全通过。
- 第三关：无审核版三遍 **40/40/40**（均值 40.00，噪声带 0）；原版 [40,39,39] 均值 39.33、噪声带 1。均值差 +0.67 **< 噪声带 1 → 判「能力没变」**，分类无一下降（中文 7.33→8.00）。
- 三张表 + 环境说明 + 复现命令 + 撤回方法都写进 `abtest\RESULT.md`。
- **我那个「约 90 分钟」的估计是错的**：按单次 26.6 秒算的，那是长题；实测拒答关 10 分 42 秒、能力关 6 分 05 秒。以后估耗时先用同类请求的实测均值，别拿单次极端值。
- 显存：本会话 LOW-VRAM 警告只 1 次（切换后首个请求），之后没再刷 → 暂不改 `--vram-reserve-mib`。decode 63.8~67.3 tok/s（上下文约 8 万 token 时）。
- 现状：机器停在无审核版。撤回 = 双击 `切回原版.bat`；再切回来 = 双击 `切到无审核版.bat`（pack 已建好，只剩读模型，几分钟）。
### 10.15 原版模型已删除，机器只留无审核版（2026-10-18 12:2x）

- 删前实测原版占用：`models/IQ3_XXS` 71 GB（shard1 47039860096 + shard2 28800138432）+ `packs/iq3_xxs` 1.5 GB = **72 GB**。
- **先证明没被占用再删**：两个目录直接 `mv` 改名成功（占用中的文件改名会失败）→ 再发一条真实请求，引擎正常回答 → 才真删。
- 删完再发一条：回答「还在」，97 token ✓ 引擎没受影响（说明没有东西在懒加载原版文件）。
- 删后 D 盘：**333 GB → 405 GB** 空闲（`df /d`）。
- 保留：`models\mmproj-Qwen3.8-Flash-Next-BF16.gguf`（两版共用的视觉投影，配置里 `vision.mmproj` 指着它）、`data\expert-profile.bin`、`mtp\rt`、两个 `packs\sc117_iq3_xxs` + `models\sc117_iq3_xxs`、配置备份 3 份、`第一关_张量对比.json`（里面有原版 shard1/shard2 的整文件哈希，原版文件没了这份证据也还在）。
- `切回原版.bat` 已改成「说明型」按钮（GBK/CRLF 实测 226 字节、裸LF 0）：双击会用中文告诉他原版已删、要恢复找助手重下（约 71 GB、2 小时上下）。`dl-sc117\继续下载.bat`、`看下载进度.bat` 已删（下载完就没用了）；`dl.sh` 留着，里面有下载地址。
- **新坑（差点以为删了）**：`rm -rf` 用相对路径时，我的 shell 工作目录其实已被重置回 `E:\Desktop\aigz`，路径不存在但 `-f` 不报错 → 打「删除完成」其实一个字节没删。教训：**跨盘/绝对路径的删除一律写绝对路径，删完必须 `ls` 复查 + 看 `df` 数字对不对**（这次靠 df 从 333 没变才发现）。
- 配置备份里 `.bak-sc117-20261018-114831` 内容是原版配置，里面写的原版路径现在已经不存在了；真要回原版得先重下模型。

### 10.16 「刚才速度异常」诊断完了：显存见底 → 驱动换页 → decode 掉到 4~5 tok/s（2026-10-18 21:0x，判据全在引擎日志里）

**现象（实测数字，全从 `D:\Strata\Strata-main\strata-iq3_xxs.log` 直接抓）**
- 19:12:51 那次启动的会话里，decode 从正常的 60~80 tok/s **崩到 4.1 / 4.5 / 4.6 / 4.9 / 5.1 tok/s**（约 15 倍慢），连读入（prefill）也崩：`5.9 tok/s`、`6.1 tok/s`。
- 最惨一条：`prompt 46595 ... 2906 generated in 565948 ms (5.1 tok/s)` —— 一次回答跑了 **9 分 26 秒**。七条加起来约 22 分钟。
- 翻车的那一条正好在上下文最大的地方：`prompt 144327 tokens ... read in 3540 ms (5.9 tok/s), 143 generated in 35247 ms (4.1 tok/s)`。它前面 133K~144K 的十几条还是 57~76 tok/s。

**真因（引擎自己打印的，不是我猜的）**
- 那次启动：`strata serve: 151 MiB of VRAM free with everything loaded - LOW: requests may stall; add --vram-reserve-mib 1061 to the config's args (or lower --max-context)`。
- 每条请求开头：`WARNING: only 139/142 MiB of VRAM free at the start of this request (below 1024 MiB): ... the driver can page GPU memory to system RAM, decode falls to a few tok/s and a window may never finish (#2065)`；抓 verify 窗口时只剩 `0~83 MiB`。
- 专家缓存被自动压缩：`expert cache auto: 4.95 GiB free, 700 MiB reserved -> 1884 slots` → `only 0 MiB free ... shrinking` → 实际 **1698 槽**（20:56 那次是 1753 槽）。
- 页面文件也紧：`Windows commit: 14.8 GiB left of a 84.7 GiB limit`（现在 19.9 GiB）；物理内存现在 59.6/61.7 GB → 换页代价极高。

**两条要记住的结论**
1. **掉进换页自己爬不出来**：崩了之后即使对话回落到 3.7 万 token，还是 4.6 tok/s；**只有重启引擎才恢复** —— 20:56:08 重启后第一条 64.3 tok/s、随后 68.9 / 69.2 / 67.5 / 70.9，全部正常。这就是判据（不是网络、不是磁盘、不是量化档位、不是提示词）。
2. **不是别的应用抢显存**：19:12 和 20:56 两次启动，引擎算出的可用显存都是同一个 `4.95 GiB free` → 差别只在自动缩缓存缩到哪。18:31 那次生图（4 张 1184x832、309.2 秒，见 `素材\工作\runs.log`）脚本已按设计关掉 ComfyUI；现在 `netstat` 里 8188 没监听、没有 blender 进程。所以是**引擎自己把专家缓存吃到只剩 151~359 MiB**，上下文一大就没缓冲可用。
- 加重因素：无审核版模型（今天中午切的 SC117）把 96 个专家升到 Q8_0，显存比原版更紧（10.13 节已记过同类警告 `only 50 MiB free`）。

**已改（2026-10-18 21:0x，老大说「试试吧」）**
- `D:\Strata\Strata-main\strata-iq3_xxs.json`：`--vram-reserve-mib` **700 → 1061**（引擎 LOW 警告自己给的数）。
- 备份 `strata-iq3_xxs.json.bak-vramres-20261018`（1833 字节）。撤回 = 双击 `abtest` 之外没有现成 bat，手动复制回去即可：`cp` 备份覆盖配置再重启。
- 实测校验：python `json.load` 通过并打印 `vram-reserve = 1061`；`diff` 备份 vs 现配置 **只有第 26 行一处差异**（700→1061），别的字节没动。
- **还没生效**：改配置必须重启引擎。给老大的操作 = 先双击 `E:\Desktop\aigz\strata-bench\D散文件\stop-strata.bat`，再双击 `D:\Strata\Strata-main\START-HERE.bat`。
- 重启后验收要看三样（读引擎日志 `strata-iq3_xxs.log` 最近段）：① `expert cache auto ... -> N slots` 和 `shrink` 后实际槽数（原来 1753，改后应少约 200 槽）② `XXX MiB of VRAM free with everything loaded` 是否脱离 LOW（原来 359）③ 我自己的请求 decode tok/s（重启前同量级上下文 56K~64K = 66.0~70.9）。**注意本机同配置 decode 自己会漂 ~9%，差值小于 9% 不能算变慢**（见 `knowledge/bench-ab-and-docs.md`）。
- 重启后第一条消息会特别慢：前缀缓存没了，我的上下文约 6.6 万 token 要整段重读（重启前实测 37K 读了 37.5 秒）→ 别当成又崩了。

**没做的事 / 下一步等老大拍板**
- 还没改配置：`--vram-reserve-mib` 仍是 700。引擎给的两个数：LOW 那条说 **1061**，请求开头那条说 1600。推荐先按 **1061** 提一档（代价：专家缓存大概少 ~200 槽，decode 可能慢 1~3%，改完必须重启引擎=老大双击 `START-HERE.bat`，而且要同种子 A/B 实测才知道掉多少）。
- 更便宜的土办法：对话上下文**超过 ~12 万 token 就交接重开**（`/metrics` 的 `conversation_cache.last_prompt` 读数，别等它自己崩）。
- 别再试的方向：换量化档、改提示词、重启电脑 —— 这次的现象跟这些无关；同一个进程里怎么聊都回不来。

### 10.17 `--vram-reserve-mib 1061` 已生效并验收（2026-10-18 21:1x，老大双击 stop + START-HERE 重启）

**切换真的生效了（判据 = 引擎实际命令行，不是嘴上说）**
- `engine started: ... --vram-reserve-mib 1061`；`expert cache auto: 4.95 GiB free, 1061 MiB reserved (+184 MiB for the draft head) -> 1722 slots` → 自动缩后实际 **1603 槽 / 2.64 GiB**（改前 1753 槽 / 2.88 GiB）。

**改前 vs 改后（本机 12G、同一份配置其余项没动、同一模型）**
| 指标 | 改前(700) | 改后(1061) |
|---|---|---|
| 专家缓存槽 | 1753（2.88 GiB） | 1603（2.64 GiB，少 150 槽） |
| 全装完剩显存 | 359 MiB | 571 MiB |
| 请求开始时剩 | 142 MiB（后来一路掉到 **11 MiB**） | 367 MiB |
| verify 窗口时剩 | 0~83 MiB | **265~273 MiB**（上下文更大时测的） |
| 启动有没有 stall 警告 | 有（151 MiB - LOW） | 没有 |
- **崩速过程的真相**：改前那次空闲显存从 142 → 11 MiB 一路见底（对话越长、检查点越多越紧）→ 见底就换页 → decode 4~5 tok/s。所以「留余量」是对症的。

**速度账（诚实版）**
- 改后我的请求：`prompt 93629 = 0 reused + 93629 read in 98461 ms (950.9 tok/s)`（重启后第一条全量重读，98 秒，符合预期）；之后 decode **63.5 / 62.0 / 59.3 / 65.8 tok/s，上下文 94K~97K**。
- 改前参考：56K~64K 上下文时 66.0~70.9；133K~144K 时 57~76。上下文越大 decode 本来越慢，加上本机同配置 decode 自己漂 ~9% → **现在的 59.3~65.8 不构成「变慢」的证据，也没有变快**；省下的 150 槽换来的余量目前没看到代价。
- 命中率：改后 58.3~67.7%，改前同日 57.2~77.3%（本来就大幅波动）→ 看不出掉了。

**结论**：这次改动值（余量翻倍 + verify 窗口脱离 0 + 不再有 stall 警告，速度没看到损失）。
**仍然要守**：引擎还是报 `only 367 MiB ... below 1024 MiB`、建议 1728 —— 上下文堆到 13 万以上余量照样会见底。**硬规矩：对话超过 13 万 token 就交接重开**（上次崩在 144327；`/metrics` 的 `conversation_cache.last_prompt` 就是仪表，现在 97912）。
撤回：把 `strata-iq3_xxs.json.bak-vramres-20261018` 复制回 `strata-iq3_xxs.json`，再双击 stop + START-HERE。

### 10.18 纠正一个我说错的结论：降 `--max-context` 省的是内存不是显存（2026-10-18 21:2x，老大问「不是在内存里吗」，他是对的）

- 日志两行铁证（同一开关、只有 max-context 不同）：
  - 以前 `max-context 131072`：`KV streaming: 32768 of 131072 cells per QSA layer in VRAM, the K/V in 1.55 GiB of pinned RAM`
  - 现在 `max-context 262144`：`... the K/V in 3.09 GiB of pinned RAM`
  - → max-context 翻倍，**内存里的整条 K/V 从 1.55 GiB 变 3.09 GiB（成正比）**，而**显存里给 KV 的部分永远是「每层 32768 格」，跟 max-context 无关**。
- 所以：**降 max-context 到 147456 只省约 1.35 GiB 内存，不省显存、换不来专家槽、不会更快**。我 10.17 之后口头说过「省下的显存去换槽」—— 那句是官方对 `--kv-resident` 的说明，错安到 max-context 头上，**作废**。
- 真想「赚槽」的开关是 `--kv-resident`（显存里 KV 的地盘是它定的）：32768 → 最小值 20480 按比例约腾 150 MiB ≈ 90 槽（**按 3.09 GiB/262144 格推的，本机没实测**，代价 = 更早开始从内存搬 KV）。老大说「不用」→ 没测。
- **机器现状（老大拍板：不再动）**：`--vram-reserve-mib 1061`（已生效）/ `--kv-resident 32768` / `--max-context 262144` / `--kv int8` / IQ3_XXS 无审核版。**别再提议改 max-context 来提速**，那是内存的账。
- 自动开新会话已实测通：`mcp__cherry-tools__session_create` → 新会话 `27c5b515…` 回「收到」并送达本对话（`outcome: success`）。规矩已写进 `SOUL.md`（超 131K 就写交接 + 自己开新会话 + 告诉老大去新会话；界面上切换/删旧窗口仍要老大点）。

### 10.19 分支/未合并 PR 全扫一遍：本机暂无可用优化，立三条观察项（2026-10-18 深夜，老大问「分支有无优化方案」）

- **怎么查的**：GitHub API 列分支/标签/open PR + 12 个相关 PR 正文全文读。判据实跑：`main` 与 v0.1.45 tag **领先 0 个提交**；分支只有 main + 旧 `rc/0.1.30`（最后提交 9-30）。open PR 140+ 个，标题全看，正文全文读了 12 个（存档 `strata-bench\pr\2763/3063/2791/2861/3037/2830/2862/3060/2835/2719/2838/2774.md`，PR 列表 `_pulls.json`/`_pulls2.json`/`_branches.json`，0.1.45 发布说明全文 `更新说明-v0.1.45.md`）。
- **直接出局**（机器不对口）：#2763/#3063/#2791（32G 内存机的低内存模式测速报告——顺带证实内存足的同款 12G 机器能到 90~117 tok/s，本机就在好档）、#2861（多卡分层才有的 per-part 显存留量）、#3060 RAM_ADAPT（给内存装不下专家的机器用，本机装得下）、#2838 arena_budget（内存侧上限，本机不缺专家；它的 STOP.bat 本机早有等价物）、#2719 prompt-cache-spread（场景 = 客户中途改写老历史再重读，Cherry 是尾部追加型，收益低且多留 checkpoint 占显存没测）。
- **作者自己实测「没赚到」的，别追**：#2862（MTP 草稿头专家升 Q8_0/BF16：命中率不变、白亏约 900 槽）、#2830（MTP_ROOM_MIN 长提示词借草稿头地盘：第一个形状实测「works, bought no time」，新形状运行时没跑过）。
- **观察项（等官方合并进 main 再动，本机装的是官方 Windows 编译版，open PR 用不了；自己编源码风险大于收益）**：
  1. **#2774 短提示词读取提速**（最对症）：5070 Ti + GSQ-RCO 同族，<1000 token 的追加读取实测快 25~33%（177 tok 473→315ms）；其中 ROUTE_PRIOR 部分会变输出且质量没测，DIRETTO 部分号称走同样的计算。**合并后：全文读 diff → 同种子 A/B 测每轮 TTFT**（本机 decode 漂移 9% 的规矩照旧）。
  2. **#2835 MMQ_SLAB**：显存满时「读提示词中途 malloc 失败 → 引擎当场死」的保险（本机显存常态 95% 满就是这个敞口）；不提速，代价 = 少 40 来个借出专家槽。
  3. **#3037 WDDM checkpoint/存档拷贝损坏修复**（262144 上下文下输出变 NaN，#3036 是完整复现报告）：本机同为 Windows + 262144，目前没观察到症状，**一旦见到 NaN/乱码先怀疑这个**。
- **下一步触发条件**：**0.1.46 发布时 → 全文读发布说明 → 若上面三条有被合并/转正 → 按「先证明切换生效 + 同种子 A/B + 多指标 + 目视」流程测 #2774**。老大说「可以」才立的这条备忘。

### 10.20 更新监视执行：官方跳过 0.1.46 直接发 0.2.1，三条观察项全灭，结论=暂缓更（2026-10-20 深夜，老大说「看更新」）

- **查了什么**：GitHub API releases/tags + 0.2.0-beta 与 0.2.1 发布说明**全文读**（存档 `strata-bench\更新说明-v0.2.x.md`）+ 三个观察 PR 的合并状态 + v0.2.1→v0.2.1.1 对比。
- **版本线实况**：10-17 发 0.1.45（本机在用）→ 10-19 13:52 UTC 发 **0.2.0-beta** → 10-20 08:19 UTC（北京 16:19）发 **0.2.1** → 当晚打 tag **v0.2.1.1**（=0.2.1 之后 6 个提交，内容只有 Docker 修复 + Windows 长路径安装热修，发布说明明说「app 和引擎不变」，只换 Terminal 0.1.46.1）。引擎包版本 = 0.1.46（0.2.0 时代是 0.1.45.3）。
- **三条观察项终局（API 实查）**：#2774 **closed 未合并**、#2835 **closed 未合并**（10-19 关）、#3037 **closed 未合并**。→ 10-18 立的触发条件作废：最对症的短提示词提速官方不要了，0.2.1 里没有等价的 NVIDIA 短提示词改动。#3037 的教训保留：**本机一旦出现 NaN/乱码仍先怀疑 WDDM checkpoint 拷贝这条**（修复没进主线）。
- **0.2.1 对 5070 Ti 12G + Windows 的实际增量**：新默认几乎全是 AMD/Linux/Mac/双卡/smem86·60 老卡；对 NVIDIA 单卡本机**没有任何一条带 50 系实数的改动**。唯一参考数字：原作者在 P100(sm_60)/A4000(sm_86) 上实测 0.2.1 tip 解码比 0.1.45 快 7~10%（已知限制节，不是本机）。0.2.0 的 sm86/sm60 解码提速表（+10~14%）不对口 Blackwell。值得留意的两条：#3215 修复「app/setup 每次 Load 强改 --vram-reserve-mib」正好是本机手工调过的开关（本机走 json+bat 不受 app 摆布，影响小）；0.2.1 起「MTP 草稿层计入显存配额和专家缓存计算」→ 更上去 1061 留量和专家槽会重算，**必须重新验收**。
- **结论（给老大）**：**暂缓更**。理由：① 等药方三条全没合并，更了不带来最想要的提速；② 50 系+Windows 零实测数；③ 0.2 大版本重排了安装/更新结构（app+Terminal+签名引擎流三件套），当天才出、当晚就打热修，让别人先踩；④ 引擎=助手本人，坏了当前对话直接断。更的方式（真要更时）：0.2.1 全量安装器装**新目录**、0.1.45 原地不动可撤回、指回模型目录、bat 重指、按 A/B 规矩重验收。
- **下次触发条件（替代旧的）**：a) 出 **0.2.2/0.2.3** 且发布说明出现 **RTX 50 系（sm_120）或 Windows 的实测条目** → 全文读说明再报；b) main 上出现 #2774/#2835/#3037 的重开版（新 PR 号）并被合并；c) 本机出现 NaN/乱码（先疑 #3037 那条线）。

### 10.21 0.2.1 已装进独立测试目录（引擎+全套服务栈），等老大双击实测切换（2026-10-20 深夜，老大批「装到新目录测试」）

- **位置**：`E:\Desktop\aigz\strata-0.2.1-test`（中文显示名「测试Strata021引擎」，desktop.ini+attrib 已用 Shell.Application 读回验证）。0.1.45 的 D 盘安装**一个字节没动**，撤回 = 老两招（双击 stop-strata.bat 再双击 D:\Strata\Strata-main\START-HERE.bat）。
- **装了什么**：官方引擎包 `strata-engine-0.1.46-windows-x86_64-cuda-cuda13.tar.gz`（553 MB，SHA256 与官方清单逐字核对通过，直连 github 2.5 MB/s；gh-proxy 同日实测只有 0.13 MB/s 别再用）+ **0.2.1 完整源码**（27 MB tar 包，解压在 `stack\`）+ **照搬的 .venv**（714 MB，Python 复制，7408 文件数核对一致）→ 全在 `stack\` 里：`stack\engine\` 放 0.1.46 引擎（自带 cublas dlls，BUILD.json archs 含 sm_120），`stack\strata-iq3_xxs.json` = 老配置只改 5 处路径，17 个引擎参数 + STRATA_ADAPT_OVERLAP/NO_LARGEPAGES/ROUTE_RESIDENT 三个 env + port/idle/vision 全原样，模型仍指 D 盘原文件（只读复用）。
- **兼容性实测**：① 新 exe 在本机 `--version` = 0.1.46 正常；② 老 json 的 17 个参数**全部还在**（`--help` 没列 `--vram-reserve-mib/--adapt-every/--adapt-decay` 三个，害得我先误判「没了」——源码 `program/generate.cpp:2513,2568,2569` 实锤它们照常解析，只是帮助文本没写）；③ **0.2.1 服务入口 = `python -m serve.server --engine strata --config xxx.json --port 8080`**，spawn 引擎的契约（`[exe,--serve,*args]`）与 0.1.45 一致；④ mock 引擎冒烟已通（8099 端口、无显卡、/v1/models 正常返回、依赖零缺失）。
- **怎么测**：双击 `测试新引擎.bat`（bat 内容纯 ASCII 已核验非 0）。流程=按 stop-strata 同法停当前 8080 → 新窗口起 0.2.1 栈 → 每 10 秒向 8080 发一条真问题（req.json，max_tokens 8），最多等 25 分钟 → 得到回答写 test_log.txt + nvidia-smi 留证；**超时自动回滚**（杀新栈 + 自动跑老 START-HERE 恢复 0.1.45）。双击期间助手（8080）会断，属正常（和日常重启引擎一样）。
- **踩过的坑（别再踩）**：a) gh-proxy 当天 0.13 MB/s，直连 github 反而 2.5 MB/s（10-20 晚实测，与 10-20 早的坑反向了，直连不行再换代理，两边都试）；b) Bash 工具的持久 cwd 会被重置，**相对路径必炸**（src.tar.gz 找不到/robocopy rc16 全是这个），一律绝对路径；c) `mv` 大目录报 Device or resource busy（索引器占用）→ 直接复制别死磕；d) robocopy 对这棵树反复 rc16，Python copytree 一次成功且要数文件数核对；e) bat 危险行自查：rollback 段曾写了一条 `taskkill /FI "WINDOWTITLE eq python*"` 会误杀所有 python 窗口（含 Cherry 的），已删，标题过滤器只认 `StrataTest021*`；f) Python 里拼 Windows 路径用 `chr(92)` 数反斜杠，heredoc 里手写 `\\` 会被吞（两次 SyntaxError）。
- **验收看什么**：test_log.txt 出现 `NEW 0.2.1 ENGINE OK` + nvidia-smi 显存数字应接近旧版（专家缓存 ~1603 槽、剩 ~571 MiB 量级，新版权威改了 MTP 计入配额，槽数变化要留意）；然后在 Cherry 里发一条消息看回答和速度。**没跑过真实切换之前，这一切都还不算验证过。**

### 10.22 真实切换实测（22:12~22:25）：新引擎能起能答但第 4 次启动自杀，最终回滚赢，当前在跑 0.1.45

> 本节第一版曾误记「新栈接管」——22:25 用进程表复核后纠正：回滚赢了，现服务/引擎全在 D 盘老路径（进程创建 22:15:42/22:15:45 + D 盘日志写到当下，三件套实锤）。教训：**判身份只认「进程可执行路径 + 创建时间 + 日志 mtime」，别信 metrics 的 version 字段**。

- **实况**：老大双击 4 次（22:12:15/12:45/13:34/15:02）。前两次撞车（第一次没加载完就被第二次杀了重来）；**22:13:26 真成功**：新引擎满载 11168 MiB 并答出 8 个 token（resp.json 为证）。run3 也起成功（日志「everything loaded，剩 511 MiB」）。**run4 新引擎 22:15:16 启动尾声自杀**——最后一行正是它自己的警告「little room for the verify windows' buffers under WDDM; if the engine exits right after this line...」= 本机 10-18 认得的 WDDM 显存见底敞口，这次崩在启动期。之后 run1 遗留轮询超时走回滚：杀 LISTEN + 跑老 START-HERE → 老 0.1.45 于 22:15:42-45 复活，run4 的 E 盘服务也被回滚的 taskkill 捎带清掉。
- **新引擎起机级实测**：`--vram-reserve-mib 1061` 照常生效；专家缓存 **1596 槽**（老 1603，-7）；MTP 草稿层实占 **835 MiB**；满载剩 **511 MiB**（老 571）；**请求起点只剩 409 MiB**（触发引擎自带 <1024 警告 = 老引擎崩过的同一片区）。0.2.x 新代码实锤行齐全（pinned headroom、PCIe 14.4GB/s、MTP 3609MB/s）。
- **当前老引擎真数（老大问速度时的状态）**：decode 平均 **63.7 tok/s**（19637 tok/308s，13 请求累计）、接受率 **83.0%**、11.6 GB 占用、83℃——与基线（61.6 / 84.7%）持平略好，无异常。
- **对 0.2.1 的结论（修正）**：「参数全兼容、能满载起、能回答」✓；但**同留量下 MTP 把余量挤薄 → 409 MiB 警告 + 一次启动期自杀**是拦路问题。下次只改一个变量：**--vram-reserve-mib 1061→1536**（引擎警告给的方向），代价 ~100 槽，按同种子 A/B + 先证明生效再下结论。bat 加固：开头加「已有实例在跑就退出」锁（tasklist 判 StrataTest021* 窗口），杜绝撞车+误回滚。
- **操作教训**：双击一次后等 test_log 出结果再点下一次；遗留轮询循环会触发误回滚（这次就这么退的）。

## 10.23（10-20 深夜：1536 那次测试的真实结局）

**测试本身成功，但没人接班 —— 新引擎加载完 3 分钟后被关掉了。**

时间线（全部有进程创建时间/日志 mtime 佐证）：
- 22:29:03 老大双击测试 bat（这次只点一次，锁生效没重复启动）→ 22:29:22 ping 就通了（NEW 0.2.1 ENGINE OK）。
- 22:29:37 新引擎 0.1.46 **完整加载完**，关键数字（reserve 1536，本机 12G）：
  - expert cache auto 算出 1504 槽 → 写满后只剩 277 MiB → **自动缩到 1197 槽（1.97 GiB）**
  - **全部装完剩 1123 MiB**（1061 时只有 511 → 1536 确实退出了 <1024 的危险区）
  - 这次日志里**没有** "below 1024" 警告、没有 startup 自杀
- 22:32:06-09 8080 上出现的却是**老 0.1.45**（serve PID 2640 / engine 15904，路径都在 D:\）。新引擎的 serve 窗口没在进程表里 —— 死因：serve 窗口被关掉（很可能随测试窗口一起关了），引擎随父进程一起退。随后有人双击了 D 盘 START-HERE.bat（setup.py + serve 22:32:07 起）。
- 当前 8080 = 老 0.1.45（已核对：进程 exe 路径 + 创建时间 + D 盘日志 mtime 三项一致；/metrics 的 engine.version 字段仍不可信，照旧）。

**结论**：
1. reserve 1536 修好了「启动即自杀」和余量警告（1123 > 1024），**代价是常驻专家槽从 1596 掉到 1197（−399 槽）** —— 速度会不会掉，**还没测**（引擎撑到答完一个 8 token 的 ping 就被关了）。
2. 要得出「0.1.46@1536 能不能接班」，还差一步：**让新引擎稳定跑着、发真实长请求，量 decode t/s 和接受率**，跟老引擎 61.6~63.7 t/s / 83~84.7% 对着比。
3. 测试窗口的教训：**serve 窗口（标题 StrataTest021 那个最小化窗口）关了 = 引擎就死**；测试出 OK 后别关那两个窗口。

**下一步（等老大确认）**：我用自动模式自己切一次（挂 60 秒延时点火）：开 0.1.46@1536 → 稳定后发 3 条真实请求量速度 → 报数字 → 老大拍板接班还是退回。

## 10.24（10-20 22:44~22:55 自动切换两次失败的教训）
- **坑A：Bash 工具里 `nohup pythonw 延时脚本 &` 不可靠** —— 点火进程在工具调用结束后被杀，65 秒延时从未触发（22:44 装的，22:48 已死）。别再单独用 nohup 挂延时。
- **坑B：MSYS bash 里 `cmd //c start Xxx /min cmd /c "..."` 不带引号的窗口标题会被当成命令名**，整个 start 失败且管道挂起（TaskStop 手工停掉）。要用 start 必须 `start "标题"` 带引号。
- 22:55:16 进程级核实：**只有老引擎在跑**（serve 2640/engine 15904，都 22:32:07-09 创建，路径 D:\），8080 正常、无异常；E 盘 serve 从未启动过，test_log 无新 run 记录。
- **最可靠的自动切换路 = 老大双击**（今晚 5 次双击全部成功）。ASCII 副本 test_engine.bat（与测试新引擎.bat 逐字节 cmp 一致）已备好。切换成功判据：test_log 出现新 "test start"+"NEW 0.2.1 ENGINE OK"，且监听 8080 的 python 路径在 E 盘 strata-0.2.1-test\stack。

## 10.25（10-20 23:00 切换成功：0.1.46@1536 已接管 8080，正在实测）

- 23:00:26 老大双击 test_engine.bat → 23:00:44 NEW ENGINE OK（18 秒）；23:01:25 第二次点击被并发锁 SKIPPED（锁生效）。
- 身份核实：监听 5744 = `-m serve.server`（E 盘 stack 的 venv 重执）、引擎 17396 23:00:35 起、D 盘引擎 15904 已被杀。/metrics engine.version=0.1.46 且这次与进程证据一致。
- 关键数字（本机 12G、reserve 1536、262K ctx）：槽 1504→自动缩到 **1109**（比 22:29 那次的 1197 又少 88）；全装完 **剩 1348 MiB**；无 below-1024 警告、无自杀。
- 真实负载速度（引擎自己记的逐请求 decode tok/s，含我自己 = 28 条非零样本）：**均值约 65，尾段 88~90**；老引擎基线 61.6~63.7 → **没变慢，略快**。
- 猜中率：totals 898/1120 = **80.2%**（老基线 83~84.7%，略降；日志另记 suffix drafts 242/273=88.6%）。
- KV 流式 96.51% 命中 VRAM；route tail skip 已跳过 11992 次 missed expert（新引擎靠它补偿少 494 个常驻槽）。
- **结论（初评）：速度无损、显存余量 571→1348 MiB（安全边际大幅改善）→ 倾向让 0.1.46 长期接班，观察 1~2 天无 NaN/乱码/自杀再定案。** 以后开机双击 test_engine.bat 即可（D 版 START-HERE 留作退回）。

## 10.26（10-20 23:10 转正：0.1.46 成为日常引擎）

- 老大拍板「换新版」。已做：
  1. **桌面新增「启动新版引擎.bat」**（E:\Desktop\，另有同名副本在 strata-0.2.1-test）：内容与测试 bat 同逻辑、全绝对路径（%~dp0 全替换掉了）、ASCII+CRLF、findstr 行与原版逐字同形。功能：锁（StrataTest021 窗口在 = 已在新引擎上 → SKIPPED 不动）→ 杀 8080 上的一切 → 启 E 盘 0.1.46 栈 → 轮询 OK；超时自动回滚 D 盘老版。SHA256 两份一致。
  2. **文件夹显示名改为「新版引擎」**（desktop.ini 修掉过一次双 BOM 坑：python utf-16 写 ﻿ 会再叠一个 BOM → 写正文时不要再手加 BOM）。Shell.Application 读回 = 新版引擎。
  3. **FACT.md 已改**（备份 FACT-backup-20261020-2315.md）：正式栈/启动方式/退回方式/身份判定全部更新，1061 那条定案已标注"仅适用 0.1.45"。
- 以后开引擎 = 双击桌面「启动新版引擎.bat」；老 0.1.45 退回路 = stop-strata.bat + D 盘 START-HERE.bat（原文件未动）。
- **未做/待观察**：面板（strata-panel）的 D 盘改动不会自动出现在 0.1.46 自带网页里；1~2 天内盯 NaN/乱码/自杀，定案标准：连续正常 + 无 below-1024 警告。新触发条件（0.2.2/0.2.3 的 RTX50/Windows 实测条目、#2774/#2835/#3037 重开）继续盯。

## 10.27（10-20 23:20 老大指示：D:\Strata 才是正经引擎地址，把新的搬进去）

已完成（全部有核验输出）：
1. **老引擎 0.1.45 整树备份** → `D:\Strata\Strata-0.1.45-backup`：13564 文件 / 1,320,847,503 字节，与原件**逐字节统计一致**。它的 START-HERE.bat 保留原样 = 退回入口。
2. **搬树**：老树改名挪到 `D:\Strata\Strata-main-old-tmp`（待新引擎跑通后删）；E 测试栈整树复制进 `D:\Strata\Strata-main`：11951 文件 / 1,702,704,178 字节两边一致。
3. **配置改路径**：`D:\Strata\Strata-main\strata-iq3_xxs.json` 里 5 处 E 盘栈路径全改 D 盘（exe/cwd/log/vision/lib_dirs），改后 JSON 解析通过、E 字引用剩 0。expert-profile 仍指树内 data\expert-profile.bin（新旧两份同为 196632 字节，内容一致）。模型/包/MTP 一直在 D:\Strata\Strata-data，没动过。
4. **启动入口**：`D:\Strata\Strata-main\START-HERE.bat` 重写为新版启动器（ASCII+CRLF、锁挡重复、超时自动回滚到 0.1.45-backup）；桌面「启动新版引擎.bat」同步改成 D 路径（两者等价）。日志落 `D:\Strata\Strata-main\engine_log.txt`。
5. E 测试文件夹显示名改「旧测试已搬去D盘」（Shell 读回核验）。FACT 已更新（备份 FACT-backup-20261020-2326.md）。

**待办**：老大双击桌面「启动新版引擎.bat」完成切换（当前 8080 还跑在 E 盘那份上）→ 我验收（身份=进程路径必须在 D:\Strata\Strata-main）→ 跑稳后删 `Strata-main-old-tmp` 和 E 盘测试树。
**撤回**：双击 stop-strata.bat 再双击 `D:\Strata\Strata-0.1.45-backup\START-HERE.bat` 即回 0.1.45。

## 10.28（10-20 23:25 切换验收通过 + 清理）

- 老大 23:18 双击桌面 bat 两次：第一次被锁 SKIPPED（那时还在 E 盘版本上跑，正常）；第二次 23:18:41 真切换 → 23:19:23 `NEW 0.1.46 ENGINE OK (PROD)`。
- **验收（身份按日志 mtime 硬证）**：D 盘树日志 23:23:52 还在实时写入（= 当前对话正走 D 盘引擎）；E 盘旧树日志冻结在 23:18:15。/metrics：version 0.1.46、slots 1227、全装完剩 1122 MiB（>1024 安全）。serve 新进程 23:18:48 起。CIM 查 strata.exe 时 CommandLine 为空导致格式化报错（坑：脚本里 Substring 前先判空），不影响结论。
- 顺带观察：prefill 一条 115K 提示词 716 tok/s（老引擎基线 635，条件不同仅作参考）。
- **清理**：`D:\Strata\Strata-main-old-tmp` 已删（备份树在，撤回无碍）；E 盘测试树 1.59 GB 内容已删光。**剩一个空壳目录 `E:\Desktopigz\strata-0.2.1-test` 删不掉**（目录句柄被不知名进程/Explorer 占着，内容已空、无害）—— 下次重启或老大关掉该文件夹的 Explorer 窗口后双击删即可，别再耗回合追它。
- 新坑记录：删目录前先 `cd` 出去（终端 cwd 也锁目录）；pause 挂起的 bat 窗口要按 PID 杀（CIM CommandLine 可能为 null，按命令行正则匹配会漏）。
- **观察窗开始**：1~2 天内盯 NaN/乱码/自杀/below-1024 警告，没事写「定案」。桌面 bat 与 D 盘 START-HERE 等价、互不冲突（同一个锁标记）。

## 10.29（10-20 23:30+ 观察窗首轮体检：引擎健康；below-1024 警告会常客出现但实测无害，别当退回理由）

**身份三件套复核**：serve 引擎进程 23:18:54 起、单进程、日志持续写入到当下 = 当前对话正走 D 盘 0.1.46。无重启、无 NaN、无自杀。

**首轮就抓到警告，查清了**：日志里 5 次「everything loaded」对应今晚 5 次运行（564/511/1123/1348 四次是测试期，1122 那次起才是正式运行）——**这份 log 文件是随树搬来的，前四段是历史，读警告先对分界行号（58/122/195/247/432）**。正式运行后出现 1 条 below-1024 警告：某请求起点只剩 851 MiB（引擎建议 reserve 1728）。

**关键实测（本机 12G、reserve 1536、decode 含助手自己）**：警告之后那条请求是 **115455 token 的满长对话，decode 64.8 tok/s**；后续 117K/119K/121K 请求 59.9~76.8 tok/s —— **警告出现了但速度没掉、没换页、verify 窗口全部捕获无错**。本会话 36~52K 请求 decode 61~76 tok/s。规律：**提示词 ≥约 86K 时请求起点显存降到 1015→851 MiB 触发警告**（约每 1K token 吃 5.5 MiB）；外推到交接线 131K 剩约 760、老崩点 144K 剩约 690 —— **离老引擎崩速的 11 MiB 区还有 600+ MiB 安全边际**。对比：老配置 1061 时同样位置曾只剩 409 MiB 且启动期自杀过一次。

**结论**：警告是显存余量低于 1024 的提醒（#2065 敞口），**不是故障**。定案标准里「below-1024 警告」这条要改口径：长对话出现警告属预期，只要 decode 没掉到个位数、没 NaN/自杀就不算异常。**建议维持 1536 不动**（照引擎建议上 1728 要再吃约 200 MiB 专家缓存、槽位变少，为一个不致病的提醒付速度代价不值；老大点头才改）。

**观察窗剩余项（到 10-22）**：NaN/乱码/启动自杀/decode 掉到个位数。都没事 → 写「定案」。E 盘空壳目录 `strata-0.2.1-test` 本次已删掉（rmdir 一次成功，待办②清结）。

## 10.30（10-21 凌晨：老大要看新版带窗口的桌面 app，安装包已下好，等双击安装）

- **可行性已查源码实锤（0.2.1 树内 apps/desktop+host）**：app 与咱同一套机制（json run config + serve/server.py --engine strata --port）；配置写入三层：界面 20 多个选项（含 vram_reserve_mib 输入格）→ 其余走 **user_args「手写优先」机制**（每次加载盖在自动生成参数上，setup 重写 args 也不抹掉；官方 #3215 修了强改手写 reserve）→ env 只认 `STRATA_[A-Z0-9_]+`（咱 3 个开关正好合规）。**7 个参数被划成 UI 选择题**（CHOICE_FLAGS：--max-context/--kv/--vision/--mtp/--spec-min-p/--batch-mtp/--layer-split），只能界面选、不能手写覆盖。模型支持指自己现成 GGUF 文件夹不重下（ownGgufDir，#3199）。
- **安装包已下**：`E:\Desktop\aigz\Strata-0.2.1-windows-cuda13.exe`，640,534,168 字节，**SHA256 = add88d0f…a88a 与官方 SHA256SUMS.txt 逐字核对 OK**（直连 2.9 MB/s 实速 3m35s）。清单存 `SHA256SUMS-v021.txt`。cuda13 版对咱 5070 Ti；cuda12 版 730 MB 是另一个别拿错。
- **安装准备已做**：`E:\Strata-app` 已建、中文显示名「Strata桌面版」（ParseName 读回验证）；`STRATA_COMPONENTS_DIR=E:\Strata-app\components` 已 setx 进 HKCU\Environment（app 内置引擎默认落 C 盘 %LOCALAPPDATA%\Strata\components，这个环境变量把它挪 E 盘，首次启动前已就位）。
- **坑（新增）**：① desktop.ini 开关是 `attrib +s +r 文件夹`，`attrib +D` 是无效目标；desktop.ini 已 +H+S 后 Python 'wb' 重写会 PermissionError，改前先 attrib -h 或干脆一次写对。② 安装 .exe 未签名，SmartScreen 要「更多信息→仍要运行」（官方文档原话）。③ app 引擎也占 8080，测 app 前先停咱的 bat 引擎（同日常换引擎）。
- **下一步（老大做）**：双击安装包 → 文件夹选 `E:\Strata-app` → 装完先别急，等老大开 app 后我带他指模型（D:\Strata\Strata-data 现成文件）+ 写参数 → 核对启动命令行与咱现有一致再定谁转正。**期间观察窗与在跑引擎不受影响（app 装自己目录，不碰 8080）。** 撤回 = 控制面板卸载 + 删 E:\Strata-app + setx 删除该变量，一分钟的事。

## 10.31（10-21 00:0x：app 已装好并打开过一次；另观察到 23:39 咱的栈重启过一次）

- **安装验收**：程序在 `E:\Strata-app`（strata-desktop.exe + engine-bundle + control/host/harness/node，自带全套），桌面图标 `E:\Desktop\Strata.lnk`（真实桌面就是 E:\Desktop，GetFolderPath 实锤）。引擎组件当前落 `C:\Users\kxy\AppData\Local\Strata\components\0.1.46-windows-x86_64-cuda-cuda13`（0.83 GB，C 盘还有 151 GB 空闲不紧；`STRATA_COMPONENTS_DIR` 已注册 → **下次开 app 会自动改在 E 盘重建，C 那份可删**）。C 盘 logs/install 少量文件。app 配置 `%APPDATA%\Strata\settings.json`。app 动作日志 `C:\Users\kxy\AppData\Local\Strata\logs\desktop-*.log`（host 随机端口 47831，不碰 8080）。
- **app 已自动认了咱的东西**：settings.json 里 `installs: D:\strata\Strata-main`、`data_dir: D:\strata\Strata-data`、calibration 键 = 咱的模型 qwen3.8-flash-next-iq3_xxs|131072|images，参数记录 `--pcie-frac 0.20 --spec-min-p 0.70 --adapt-every 1 --adapt-swaps 160 --adapt-decay 0.97`（**pcie 0.20 与咱实测在用的 0.40 不同**，转正核对时对齐）。app 默认 models 目录 `C:\Users\kxy\Documents\Strata\Models`，试用时要指到 D 盘现成文件（ownGgufDir 路）。
- **观察窗事件（23:39:44）**：D 盘三件套（serve/engine/vision）同秒换成新进程（serve 有 venv→重执一层，父进程一次性已退），D 日志新增第 6 段：`23:39:46 engine started: D:\Strata\Strata-main\engine\strata.exe --serve --pack … --vram-reserve-mib 1536`+ 17 参数与咱配置逐字一致、`everything loaded 剩 1124 MiB`。**判据组合（新三件套+同秒+一次性启动器已退+命令行逐字对）= 像一次常规双击重启、非崩溃**；等老大确认是否他 23:39 前后双击过 bat。速度在重启后请求里正常（本会话全程走这套）。
- **app 试用下一步的硬前置**：app 里加载模型会占 8080/吃 12G 显存 → **必须先停咱的**（双击 `E:\Desktop\aigz\strata-bench\D散文件\stop-strata.bat`，助手随之断线属正常），再到 app 里点模型加载 → 喊助手核对。撤回 app：`E:\Strata-app\uninstall.exe` + 删 C 盘 components + setx 删变量。
## 10.32（10-21 00:2x：app 拒绝咱的模型 = 白名单设计，正门 = 连接咱 8080 的 API）

- **报错**：老大选文件夹后 app 弹「unrecognized_or_unsupported_model_variant」。根因源码实锤（`strata_control/models.py` 425~465 + 239~278）：app 认模型靠 `data/gguf_fingerprints.json` 指纹表 —— 先按**文件名集合**精确匹配（`_candidate_selection`），不中再按 **tensor 数 + payload 字节 + expert 量化类型集合**三项指纹匹配（`_candidate_by_header`）；都不中 = 拒绝。咱 SC117 GSQ-RCO 改制版不在表内（名字与指纹都不符）→ **换文件夹/重选都救不了**，重下官方版才行（不值，不是现在这个脑子）。表上限 128 KiB、`UNSUPPORTED_MODEL_TYPE` 文案自带逃生门「Add it as a Custom model API (llama-server) instead」。
- **正门（已推荐给老大）**：app「设置→模型」支持连外部 API（zh.json 实锤文案：「此界面之外已有一个 Strata 服务器正在运行…或在设置→模型中连接其 API」+ 字段「API 提供商/API 基础 URL/API 密钥/API 模型别名」）→ 填 `http://127.0.0.1:8080/v1`、模型别名 `qwen3.8-flash-next-iq3_xxs`、密钥空。app 只当界面、咱 bat 继续管引擎。**代价**：app 的模型/调优页对咱引擎无效。人设/技能/MCP 可写 app 侧不受影响。
- **备选黑科技（未演）**：把咱指纹行加进 app 安装目录 `install/data/gguf_fingerprints.json`（files/tensors/bytes/expert_bytes 四项按实测填）→ ownGgufDir 就地 setup 不再重下 → app 全盘接管。风险：setup 还要在 app 数据目录重建 pack/profile（几十 GB + 几十分钟），且与咱现树争显存/端口，转正才值得演。
- **白名单底细补充实测**：`data/gguf_fingerprints.json` = 13 行（qwen 家族 = 咱这只的官方量化档 Q2_0/IQ2_XS/**IQ3_XXS(75.8GB,tensors 1224)**/IQ3_S… + swift 家族），行字段 arch/tensors/bytes/expert_bytes/experts_bpw/bpw/files；`SUPPORTED_SELECTIONS` 是 `strata_control/models.py:36` 的 frozenset 硬码。**放行需三处补丁**：指纹表加行 + frozenset 加项 + setup 的 family/model 信息条目（repo/MTP 规格；MTP 走官方草稿层可行）。**app 自动更新会冲掉补丁，每次更新要重打**；已在老大面前排序：API 连接（推荐先试）> 伪造户口（老大日常用 app 才演）> 重下官方版（否）。
- **优势盘点定调（10-21 00:3x，老大问「app 有啥优势/不太值」）**：逐条过了 apps/host 功能面（Chat/Tasks/Tuning/Monitor/Skills/Serving）+ strata_control/autotune.py、calibration.py 源码。**唯一真新货 = 自动调参**（方法论硬：交替轮次防漂移、≥+3% 且 2× 噪声才认、显存/内存 guard、崩即停、找不到增益直说"当前已最快"；需 native 管理 = 要先补白名单）。其余：带退回的引擎升级、开关一键重建——咱都有手动等价物；聊天界面/技能/MCP/监控——Cherry 都有，零增益。**拍板基调：不搬家（平迁甚至倒退，老大认同），app 定位为"借来的测量工具"**：观察窗 10-22 定案后若老大想试自动调参 → 补白名单跑一轮 tune → 赢的数字写回咱 json，Cherry+bat 照旧。API 连接（免费体验界面）随时可试，不影响任何现役。

## 10.31b 补（识别不到根因，本节原样）
- **「识别不到模型」根因（00:1x 实测）**：`/api/native` 读回 installed.models=[] 、data_folder=None、usage 全 0 —— app 新版的模型台账与老 settings.json 的 data_dir 键不相认（settings 里那三条 = **10-11 老安装遗留**，calibration date 2026-10-11 实锤，别当成"app 自动认了咱的"——收回前话）。引擎侧是好的：repo=E:\Strata-app\install、componentsDir=E:\Strata-app\components（**环境变量生效，组件已落 E 盘**）、engine usable 0.1.46 cuda。修法 = UI「选择模型文件夹」指 `D:\Strata\Strata-data\models\sc117_iq3_xxs`（装两个 gguf 的文件夹，ownGgufDir 路会就地 setup 不重下）。app 有官方中文（locales/zh.json + tune-zh.json，Settings→General→Language 切）。host 随机口 47831 的 api 可裸 GET（/api/native、/api/models 免 token，好用）。

## 10.33（10-21 00:4x：tune-spec S1~S3 完成 —— 指纹表补丁打勾，app 已验通过）

- **S2 取指纹（它自己的代码实测）**：`GGUFFile`（control/tools/gguf_reader.py）逐 tensor 求和 —— **咱七类 expert 每类字节与官方 IQ3_XXS 行逐字节相同（差 0）**；+313,309,248 全在**专家层以外**（消融版非专家侧 +302,284,800 与 shard1 体积差吻合）。expert 张量数 IQ2_S20/IQ2_XS20/IQ2_XXS18/IQ3_S26/IQ3_XXS12/IQ4_NL18/Q2_0 30。payload（它 inspect_metadata 口径）= 76,142,283,328；tensor 总数 1224（与官方行一致；shard1 内 1223 + shard2 内 1 = 1224）。
- **S3 实际只改了一个文件（比预想的三处补丁简单）**：`expert_tensor_types` 只是集合比较、expert_bytes 的数值不参与判断、models.py/setup.py 都不用 bpw/expert_bytes 数字 —— 所以 **models.py 的 frozenset 和 setup.py 注册表都不用动**（qwen/IQ3_XXS 本就在集合里有注册条目）。只改指纹表 `qwen/IQ3_XXS` 行三处：bytes 75828974080→76142283328、bpw 3.428→3.442（按字节比例换算，显示用）、files 两个文件名换成咱的（加 "abliterated-"）→ 文件名精确匹配路径直接命中。expert_bytes/experts_bpw 保持不动（实测本就相同，改了才是造假）。
- **两份拷贝都要改**（app 一份 `E:\Strata-app\control\data\` + 引擎树一份 `D:\Strata\Strata-main\data\`，补丁前两份 sha256 相同，改完仍相同）；各带 `.json.bak`。**app 每次调用都现读指纹文件，改表不用改代码逻辑；desktop app 已重启（新 pid 13248，host 47831）**。
- **验收实测**：它自己 `models.plan_import(D:\...\sc117_iq3_xxs)` = candidate_selection {qwen/IQ3_XXS, basis: known_shard_names_only}、issues []、**already_set_up 全部认下咱现成资产：config=咱现役 strata-iq3_xxs.json、data_dir=D:\Strata\Strata-data、pack=sc117_iq3_xxs 现成专家包、mtp=rt 现成草稿、mmproj** → **S4 数据接轨大概率零工作量（不用重建 pack）**。
- **坑**：① `host/server/local-models.mjs` 的 `/api/local-models/inspect` 是「本地 gguf 当聊天模型」的另一条路（自带架构白名单，qwen4exp 被拒），**不是**模型页导入路 —— 模型页走 `/api/native/local/preview`→python plan_import 直通，老大先前看到的报错就是 python 层原话，python 过了这关就通。② git-bash 给 curl 传带反斜杠的 JSON 会被吞，用 `--data-binary @文件` 或路径用正斜杠。③ 文本替换指纹表时 "GSQ-RCO-IQ3_XXS-00001" 在 swift 家族行也出现（"Swift-Qwen..." 名字里含同样子串），必须带引号锚定整串，我第一次就没锚住好在写盘前拦下。④ start 拉 app 用 bash 直接后台跑 `./strata-desktop.exe &` 成功，`cmd /c start` 反而没拉起来。
- **待办**：老大在 app 界面确认（模型页 → 「使用本地 GGUF」选 `D:\Strata\Strata-data\models\sc117_iq3_xxs`，应出现咱的模型不再报错）→ S4 确认 → S5 tune（**先停咱引擎**）。撤回本补丁：还原两份 .bak（app 更新会冲掉，重打同法）。
- **S4/S5 实查（10-21 00:5x）**：`/api/native` 顶层显示 native 侧 models=[] data_folder=null（app 自己没安装任何模型，adopt 要走它的安装流、可能触发重建），**所以 tune 不绕 app 安装，直接 CLI 打咱的 run-config**：`strata.py tune auto <target-json>` 明确支持（--help 实锤）。tune 细节：worker 起在**临时端口**（不撞 8080，但显存/安静 guard 要求先停咱引擎——guard 见「其他引擎在跑」会等 300 秒再硬测，停干净才准）；测完自动存 preset（不动咱 json）。**点火脚本 `tune-fire.py`**（自带 python 跑，90 秒延时）：杀引擎栈 = exe 在 D:\Strata 下 **或 cmdline 含 serve.server+--engine strata**（大坑：日常看护跑在**系统 python** C 盘上，光按 D 盘 exe 杀会漏，它会把引擎复活抢显存）；先父后子杀；tune 用 --mode thorough --goal speed --name tune1021 --serve-dir D:\Strata\Strata-main\serve；收尾无条件清场后用 START-HERE.bat 恢复咱正常配置、等 metrics 就绪才退出（唤醒助手验收）。
- **坑（10-21 01:0x，老大在模型页点了装/确认）**：app 的「使用本地 GGUF」只是**预览**，点安装 = **完整安装流程**：gguf 本身没重下（认出就地文件 ✓），但它会①在**它自己的目录**（C:\Users\kxy\Documents\Strata）重建一份专家包 packs\iq3_xxs ②下载 5.2 GB「加速层」(MTP 草稿，它不知道咱 D 盘已有现成的 mtp\rt 可复用)。**已取消 ≠ 真停**：界面 cancelled 后 setup.py 后台还在下载（残留 python 树 2464→5348→10264），已 taskkill 树杀 + 删净 Documents\Strata（1.9 GB），app 侧 job 记为 error（=我们杀的，正常）。**结论：调参走 CLI 直打咱 json 的路线不变，别在 app 里点安装**（点了就是 C 盘重建 7+ GB，纯浪费）。
- **第一轮 quick 调参完成（01:15~01:21，结果已存 tune-result.md + tune-report-raw.json）**：`default_confirmed/already_fastest`，baseline 65.0 tok/s 与咱日常实测吻合。**但本轮 0 候选实测**：spec3/adapt_tier_fast/adapt_decay_09 被「可能改变回答」拦（需 --allow-small-differences），adapt_async 被「不可复现」拦，kv_resident_64k 留给 thorough，pin_by_need/host_core_last/kv_grow 有它 thorough 历史 flat 记录。**待老大拍板**：A 就此收工（配置零改动）；B 补跑 thorough + --allow-small-differences（真测 3 项 + 64K 常驻，估 30~60 分钟，助手推荐 B；adapt_async 不建议——不可复现会污染它的测速法）。补跑改法现成：tune-fire.py 已是参数化（quick/thorough），加 flag 需改脚本一行。
- **坑：`--serve-dir` 必须指包根目录 `D:\Strata\Strata-main`，不是 `...\serve`**——worker 以 `python -m serve.server` 启动，指错一层直接 FAIL_BOOT「No module named 'serve'」（第一轮 8 秒就摔，rc=6）。第二次 50 秒~1.9 分钟两次自动恢复都干净（START-HERE 起、metrics 就绪才退出）。恢复后 metrics：tok_s_mean 55（含恢复期混合值，正常）。preset tune1021 已存 app 侧（id 2e484a40，对咱 json 无影响）。

## 10.34（10-21 01:4x 老大意图明确 = 想把助手本身搬进 app；可行性查完）

- 老大答「复制到app」=「相当于把你搬过去」→ 想要**助手本体**在 Strata 桌面 app 里对话（不是拷参数、不是 preset）。
- **可行性实锤（读 E:\Strata-app 安装树源码）**：app 自带**完整 agent 运行环境** —— harness = deepseek-harness 0.2.1-alpha.3（MIT，23413 文件 240 MB），host 起 `dsh --profile web` 进程经 Gateway 对话（host/server/agent/README.md）。功能面齐：bash/pwsh/文件编辑/子代理/MCP/计划任务(排程)/技能/AGENTS.md 指令加载，审批三档 Manual/Plan/Bypass（gate 卡先问后动、只读命令不问）。
- **脑子怎么搬**：profile.mjs「每 ready 本地实例 + 每存好的 API 连接各一条路由」→ app 设置里连 `http://127.0.0.1:8080/v1`（咱引擎）即当大脑，模型零安装零重建。
- **人设怎么搬**：dsh-agent-instructions 插件 = AGENTS.md 机制（从工作目录向上找 + 全局 agentsHome 一份，上限 65536 字节）→ SOUL/USER/FACT 转成指令文件即可；preset.mjs 确认 persona+agent-instructions+tool-bash/fs/jobs 全在启用清单。
- **中文界面**：harness 语言包 217 个 zh.json（find 实测）。
- **三个坑先记**：① harness 自带系统提示词比 Cherry 长 → 上下文涨更快，131K 交接线纪律必须更严；② 工具协议是 DeepSeek 设计、咱是 qwen3.8 —— Cherry 现行等价协议实测可跑（84.7% 猜中）但头一天要实测对比工具调用；③ Cherry 专属工具（session_create/cron/config 信道）那边没有，等价物 = 它自己的 jobs/sessions。
- **推荐路线（等老大确认）**：Cherry 先不拆 —— 开 app → 连 API → 拷人设与技能 → 真用几轮再拍板转正。
- 状态：app 当前没开（47831 拒连）→ 要继续先双击桌面 Strata 图标。调参补跑（A/B）仍挂着，老大不发话不跑。

## 10.35（10-21 13:3x app 侧搬家第一轮：AGENTS.md+技能已落地，等老大开新对话试脑子）

- app 状态：开着（host 47831，日志时间戳是 UTC，051340=本地 13:13 启动）。**API 连接已存在且查证 = 咱 8080**：`~\.strata\data\model-providers.json` 里 custom 连接 `http://127.0.0.1:8080/v1` openai-chat、模型别名 qwen3.8-flash-next-iq3_xxs（来源：上一轮会话/老大弄的，之前没记进 PROGRESS，本轮补实）。agent 状态 idle、harness 0.2.1-alpha.3 就绪、路由 1 条=这条 API。截图核对：老大聊天模型 chip=咱的模型、界面已中文、上下文才 5%。
- **harness 关键路径（源码实锤，以后 app 侧一切按这个）**：数据根 `C:\Users\kxy\.strata`（STRATA_HOME 未设走 ~/.strata）；agent home=`.strata\data\agent\home`（DSH_HOME 被 host 指这）；**全局人设文件=home\AGENTS.md**（agent-instructions 插件：user-global AGENTS.md + 工作目录向上找 AGENTS.md/CLAUDE.md，渲染上限 64K）；技能自动扫描四处=home\skills、agentsHome\skills、项目 .dsh\skills、项目 .agents\skills；会话记录 home\sessions\（按工作区分组）；app 的「选择文件夹」=给对话定工作区。
- **已搬（全是新文件，没动 Cherry 一个字节）**：① 写了 `home\AGENTS.md`（老大规矩全文压缩版：称呼/铁律/汇报格式/规格习惯/131K 交接纪律+app 侧「点新聊天」替代 session_create/记忆文件路径清单/技能路由路径/图视频硬规矩/环境速查）。② 整套技能 36 项拷进 `home\skills`（9 MB，删了 cherry-tool-guide —— 它讲的是 Cherry 专属工具，app 侧留着会误导）。撤回：删这两个东西即可。
- **app 侧记忆共用**：USER/SOUL/FACT 原地不动，AGENTS.md 里指路径让那边按需读；改记忆=直接编辑文件+先 cp（Cherry 的 memory/cron 工具在 app 里没有）。已知差异先记：① app 里我不能自己开新会话（要老大点「新聊天」）；② JOURNAL 追加在 app 侧没工具（结论直接写 PROGRESS）；③ cron 定时任务 app 侧等价物=它的 jobs/排程，没迁。
- **等老大做**：app 里点「新聊天」→ 输入框旁「选择文件夹」指 `E:\Desktop` → 发试机话术（写在回复里）→ 看它会不会喊老大、认不认识记忆和技能。**试机要在新对话第一轮**（全局 AGENTS.md 与技能在会话起步时才加载）。过了之后再谈：转正拍板、工作区习惯、要不要把 JOURNAL 迁成文件法。

## 10.36（10-21 13:4x 试机通过 = 搬家第一轮验收 OK）

- 老大在新对话实测（工作区 aigz）：远端助手 ① 喊「老大」拒用「您」✓ ② 引擎身份答对（D:\Strata\Strata-main 0.1.46、strata-iq3_xxs.json、reserve 1536），还自己跑了 /metrics 报真实数字（槽/余量与咱记录略有出入：它报 1137，咱记录过 1227/1126 —— 槽数随装载进度会变，不算错，但**它的数字要当线索不当结论**，核对仍回 PROGRESS）③ 技能认得出（列了 gen-image/gen-video/diagnosing/spec-lock/ab-test）。工具动作留痕「Ran 2 commands, read 2 files」= shell+读文件真的在跑。
- **待老大拍板（10.35 尾巴）**：常住哪边（我建议两边并存：app 离引擎近、Cherry 留「我自己开新会话/定时任务/多端」这些 app 没有的本事）。定了之后要做的收尾：FACT.md 加一行「app 侧助手已就绪」、JOURNAL 迁移方案（文件追加法）、cron 任务要不要在 app 侧重建。调参补跑 A/B 照旧挂着。

## 10.37（10-21 13:4x~14:0x：app 登记模型成功——下载卡点已修，参数已对齐，就差老大停引擎点「加载」）

- **app 早就会认咱的模型了**：13:41 老大点「准备并加载」触发的失败根因不是白名单——是 setup 第 4 步要先从 github 抓 llama.cpp 源码包（只为 gguf-py 校验工具），app 自带那份 `E:\Strata-app\install\third_party\llama.cpp` 是**空的**，github 当时又抽风（WinError 10060）。
- **修法（已实测）**：按 setup 的复用判据本地补齐源码：commit `3cf03257f219afbe7334045ff7c6a06ac68c627d`，下载路实测：codeload legacy zip = 404、gh-proxy 龟速（300 秒才 7.4 MB 截断）、**github archive 直连 5 秒 39.5 MB**（github 时通时不通，两条都试取快的，印证 FACT 10-20 记录）；解包进 `install\third_party\llama.cpp`（排除 tools/ui），判据两文件核验过。
- **准备已由助手代跑成功**（API 免确认：POST `/api/native/operations` {kind:install,args:{family qwen,model IQ3_XXS,context 262144,vision yes,port 8080,gguf_dir D:\Strata\Strata-data\models\sc117_iq3_xxs}}，job 13:56 起、约 10 分钟、exit 0；全程没占显存没停咱引擎）。台账 models=[iq3_xxs] ready:true、dataFolder=D、context 262144、images yes。**新专家包 packs\iq3_xxs 1477 MB 与咱 packs\sc117_iq3_xxs 1477 MB 并存**（app 自己命名体系，两份真目录不互链，E 盘空间够，别删任何一个）。mmproj 已就位（models 根，hf-mirror 下的）。
- **它写的运行配置默认丢咱参数**（`E:\Strata-app\install\strata-iq3_xxs.json`）：缺 --vram-reserve-mib 1536/--kv-resident 32768/--adapt-every 1/--adapt-swaps 160/--adapt-decay 0.97、--spec-min-p 只有 0.5（咱 0.70）、env 三个开关全没、api_monitor 等 5 个 json 键没有——**已全部并进去**（expert-profile 两处 md5 相同照用它的；exe 用它指的引擎组件=同 0.1.46；pack/tokenizer/mtp/ple 全指现成文件）。原版备份 `strata-bench\config备份\strata-iq3_xxs.app原版-20261021.json`，撤回改配置就从这份 cp 回去。
- **下一步（老大做，顺序别反）**：① 双击 `E:\Desktop\aigz\strata-bench\D散文件\stop-strata.bat` 停现引擎（Cherry 这边会断线，正常）→ ② app 模型页再点「准备并加载」（这次应直接进加载，8080）→ ③ 在 **app 里的新对话**让助手自查：启动命令行与 17 参数、/metrics 槽数与余量、decode 速度 → ④ 数字不达标就不转正：模型页停掉，双击桌面「启动新版引擎.bat」即回现状（app 台账留着无害）。
- **坑补记**：准备动作可与咱引擎共存（不碰显存）；install 的 data_dir 自动跟「下载文件夹」（现=D:\Strata\Strata-data，别再指成 models 子目录）；app 实例起来后 8080 网页=它自带 0.1.46 面板，咱定制的监控面板在 `D:\Strata\Strata-main\serve\web`（要挪过去以后再说）；Cherry 的模型指向 8080 不变，谁管引擎都能连上。
- **交接**：本对话 prompt 已到 145694（超 131K 线）→ 已开新会话接续。

## 10.38（10-21 14:4x 验收慢根因查清 = 俩引擎并跑；另查出 app 洗参数坑并已修）

- **慢 ≠ 引擎不行，是俩引擎同时在跑**：老大 14:05 点「准备并加载」时咱 13:14 的引擎还活着（D 日志一直实时写）→ app 引擎起来显存被占，它加载完只剩 1244 MiB（日志原话「1244 MiB of VRAM free with everything loaded」）→ 专家缓存槽几乎没 → 87.7% 解码专家从盘读（累计读盘 1.47 TB）→ 老大那句 16K 字的验收话术 prefill 188 秒还没完（「cancelled request keeps its conversation」）。14:24:08 咱这套又起了一次（serve python 复活引擎，参数全对、装完剩 2844），14:28 app 侧被挤死。现 8080 = 咱这套在伺候（实测 decode 74.9 t/s、专家命中 55%）。
- **stop-strata.bat 坑实锤**：它只杀 8080 LISTENING 户 + strata.exe/vision 两个 exe，**不杀 python serve** → 幸存的 serve 把引擎复活抢 8080（14:24 事故）。已补一行 powershell 按命令行杀 cmdline 含 serve.server+engine strata 的 python，放 stop 和杀 exe 之前。
- **app 洗参数坑（关键新发现）**：app 每次点加载**重写 args**，助手手改进 args 的参数洗掉三个：max-context 262144→32768、spec-min-p 0.70→0.5、vision 整块没了（实锤：json 14:09 被 app 重写；14:05 真实启动命令行就是 0.5/32768/无 --vision）。官方解 = `user_args` 键（strata_control/user_args.py 全文读过：每次启动 handwritten 值压自动生成值、setup 永不洗它、merge 无过滤对 CHOICE_FLAGS 也生效）。**已修**：user_args 追加 --max-context 262144 + --spec-min-p 0.70，vision dict 照原样补回（serve 见 vision dict 自动开视）。其余 5 参数 + 3 env 开关 app 自己接住了（14:09 版实测在位）。备份：`config备份\strata-iq3_xxs.app写后-20261021-1409.json`（app 原版备份同在，撤回按旧版）。
- **老大重跑验收的正确顺序（修正版）**：① 双击「停引擎.bat」→ 等窗口显示 Strata stopped 自动关（Cherry 断线正常）② app 模型页：上下文选 **262144**、视觉开关开（选错也不要命，user_args 兜底参数，只是视觉子进程不启动=app 里不能看图）③ 点「准备并加载」等到出现 everything loaded（此时不该再出现第二个引擎抢 8080）④ app 新对话验收：命令行含 262144/0.70/1536/32768/--vision、装完剩 ≥1 GB、decode ≥60 t/s。⑤ 达标说一声核对转正；不达标 = 模型页停掉 + 双击桌面「启动新版引擎.bat」。
- **验收前先自测**：app 引擎活着时助手自己跑 `netstat -ano | rg :8080` 确认 8080 只有 app 的 python + `wmic/Get-Process` 确认只有一个 strata.exe，再下结论谁在跑。

## 10.39（10-21 14:5x 老大拍板：不用 app 了；它的提示词/技能盘点完，捡了 3 条）

- **决定**：搬家、转正、调优工具全部挂起 —— 引擎继续咱 bat 管，Cherry 照旧。**别再主动提 app**，老大不发话不动 E:\Strata-app、.strata、D:\Strata\Strata-data\models\IQ3_XXS 里的东西。
- **在跑的大下载（要老大停）**：app 正在重下官方版 76.7 GB（普通 GSQ-RCO，**不是咱的无审核 SC117**），落点 `D:\Strata\Strata-data\models\IQ3_XXS\*.part(+.chunks)` → 老大点模型页「停止」后报一声，助手删那个半成品文件夹（只删 IQ3_XXS，**别碰 sc117_iq3_xxs**）。app 本体（E:\Strata-app + C 盘 components + .strata）先留着不卸载（无害），老大想清再撤：`E:\Strata-app\uninstall.exe`。
- **盘点结论（老大问「它的提示词和技能有什么能用」）**：① **自带技能全是空壳**：office 系 7 个只有名字没正文（资产目录没配、LibreOffice Kit 引擎没装），全树唯一真 SKILL.md 是 llama.cpp 源码包里给 llama 开发者用的 2 个 → 技能**零新货**。
- **① 修正（老大贴出技能开关页后复查，14.5x）**：有 4 个真·短技能，正文硬码在 `host\server\index.mjs:282-352`（不在 .md 文件里，先前扫漏）。逐个判：提交消息（conventional commits 规范 —— 老大不做 git，对咱没用）、发行说明（面向用户分组、省略无用户可见效果的 —— 咱「说人话」规矩已覆盖）、硬件报告（先给「能跑/勉强/装不下」结论、证据按 CPU/加速卡/内存、术语全大白话 —— 与咱 SOUL 讲性能方式一致）、代码审查（**捡了两条进 code-review-zh**：没问题就直说别凑数、别复述代码充篇幅；源+镜像 cmp 核验）。app 技能页开关 = store.skillEdits/skillPreferences，正文与咱库无冲突。② **persona 提示词**（app_session_1410.jsonl 里实录，~1300 字）：读后改、小改优先、报错一句话说清、失败了不许说成功、给人在 Windows 起 GUI 要立刻返回——大多咱 SOUL 已有。③ **已捡 3 条进 bat-and-windows-zh 技能**（源+镜像两处 cp+cmp 核验一致）：删/搬前核对目标绝对路径；强杀=退出码 1 无信号名=「中断」别当程序故障；替老大开界面点火即走+明说「已经开了」。④ 记下不动的点子：create_goal（长目标跨轮自动续跑）、subagent_fork（子代理克隆整段对话、不吃主对话上下文 —— 咱用 PROGRESS 交接等效）。它 26 个工具与 Cherry 大体等价，无新能力。
- **现状态**：8080 = 咱 D 树引擎（14:24 那段，实测 decode 74.9 t/s 健康）。10.38 的修法与两份 config 备份留着（app 万一哪天要用，点加载前照 10.38 步骤）。调参 A/B 决议：老大不用 app 后走不走 CLI 版 tune 待定，不主动跑。

## 10.35（10-21 深夜：老大要试 SC117 IQ3_S —— 下载中 + 夜里自动切换流水线）
- 起因：老大看到官方推荐 IQ3_S（64G 机器默认档），要试。SC117 仓确认有 abliterated IQ3_S：shard1 = 55,063,448,064 B（官方 sha256 40f369eca301ec6ea318dbb671b3132c26a2f0b89aa5458a7051b33215ee296c）；**shard2 与现役 IQ3_XXS 的 shard2 指纹完全相同 → 只用下 shard1，shard2 硬链不占空间**。mmproj / mtp\rt / expert-profile 全可沿用。
- 实测速度（10-21 23:52 起）：hf-mirror 单连接 7.1 MB/s、4 路并行合计 8.9 MB/s（封顶 ~9）、直连 huggingface.co 采样 0 字节不通。后台下载 dl_iq3s/dl_iq3s.sh（断点续传，日志 C:\Users\kxy\AppData\Local\Temp\dl_iq3s.log），起跑实测 9.2 MB/s，预计 ~100 分钟。
- 自动流水线：cron「IQ3S点火」(id 4a74bf4f-ea2e-40c9-b831-533409f9289a) 每 5 分钟：见 DONE → 备份配置到 dl_iq3s\配置备份-IQ3XXS切换前.json → 跑 dl_iq3s\switch_iq3s.py（硬链 + iq_pack 建 packs\sc117_iq3_s + 改配置 --native/--ple-gguf/--pack/tokenizer 四处）→ START-HERE.bat 点火 → 下一轮自查 metrics → 自动删 cron。SHA-FAIL → 停手等人。**引擎会在半夜自动重启一次（助手断线属正常），老大那时发信可能卡 2~5 分钟。**
- 内存现实：起跑时可用物理内存 6.8 GB（共 61.7 GB、占 88%），IQ3_S 比 IQ3_XXS 多 ~7.2 GiB 权重 → 悬。三种结局：正常起 / 起得来但更慢（引擎自动缩常驻）/ 起不来回滚。官方账（作者 64G 机器）：IQ3_S 质量更高（同 top-token 87.7% vs 84.5%）、**速度慢 10~15%** → 试它是试质量不是试速度。
- 撤回：把 dl_iq3s\配置备份-IQ3XXS切换前.json 覆盖回 D:\Strata\Strata-main\strata-iq3_xxs.json → 重启引擎即回 IQ3_XXS；彻底回原样再删 models\sc117_iq3_s\ + packs\sc117_iq3_s\ + 本 dl_iq3s 目录。
- 坑：① hf resolve 不加 -L 只拿到 1.3 KB 重定向页，别当「速度 2 KB/s」误判；② Git Bash 没有 free，真实可用内存用 python ctypes GlobalMemoryStatusEx；③ bash 输出中文在旧控制台会乱码但数字可读，别慌。
- 本会话会被引擎重启终结；下次开工先读本节 + 看 cron 回执。
- 【10-22 补记】单连接早高峰掉到 0.1 MB/s → 改 6 路并行抢尾（tail_dl.sh）17.75 MB/s，10:04 集齐 55,063,448,064 字节、sha256 OK、DONE 已写。点火 cron 接手：打包→切配置→重启→自查。新坑三条，别再踩：① 后台进程会被会话退出连带杀掉 —— 要脱机跑就用「bat + pwsh Start-Process bat」（Start-Process bash.exe -l 会无声卡死，cmd //c start 带引号标题会被 MSYS 剥引号搞崩，本机实测只有 bat 路最稳）；② bash 里 `${OFF+LEN-1}` 是「VAR 已定义则替换字面量」不是算术，range 要写 `-r ${OFF}-$((OFF+LEN-1))`；③ CIM CommandLine 按关键词杀进程会连自己带关键词的命令行一起杀。
- 【10-22 10:3x 切档结果】**IQ3_S 切换成功、引擎已在新档运行**（判据 = 日志 10:22:17 engine started 行 --pack sc117_iq3_s，别信 metrics 的 model 字符串，那只是配置里的旧名字标签）。实测数字：decode 冷缓存 55.1 tok/s（老档同口径约 76，官方账 -10~15% 方向一致，冷缓存有夸大）；expert_slots 1199、vram_free 518 MiB；decode 缓存命中 61.7%（老 68.2）、KV streaming 命中 91.7%（老 97.8）；strata.exe 占用 52 GB，**系统可用物理内存只剩 2.0 GB、虚拟剩 5.1 GB —— 极紧，长上下文有内存见底→pagefile 崩速风险**。要不要留这档=老大日常体感说了算（质量↑ vs 速度/内存↓）。vram-reserve 现配置是 700（切换前就如此，脚本没碰它；与 FACT「1536」记不符，待以后核）。IQ3S点火 cron 在 DONE 后曾整体消失一次（Cherry 重启疑似清空过 cron 库，原因未查），之后「点火」都是我手动干的；「IQ3S验收闹钟」cron 可能已自删，若列表里还挂名就直接 remove。

## 10.40（10-22 下午：IQ3_S 试验结束 —— 老大回退 IQ3_XXS 并已删净 S 档文件）
- 老大体感：内存太紧，拍板回退。回滚 bat 由老大自己双击，回退生效已核实（判据：日志最后一条 engine started 行 --pack sc117_iq3_xxs；配置 grep 'iq3_s' = 0 次、'iq3_xxs' = 7 处）。
- 删除已执行：models\sc117_iq3_s\（79 G）+ packs\sc117_iq3_s\（1.5 G）全删。S 的 shard2 本是硬链（与 XXS shard2 同内容），删后 **XXS 两个分片完好**（47.3 GB + 28.8 GB 原样、.done 都在），硬链按计划只掉链接没伤本体。D 盘空闲 348→400 GB（释放 ~52 GB，差额就是那个硬链的 28.8 GB，符合预期）。
- 删后内存：可用物理 6.8 GB / 虚拟 11.9 GB（比试 S 前的历史常态 4.5 GB 还宽裕，原因未深查，不影响结论）。
- 以后要再试 IQ3_S：重下 shard1（55,063,448,064 B，sha256 40f369ec…296c，见 10.35 节）+ 重跑 iq_pack + 改配置四处，shard2 硬链仍免费。配置备份 dl_iq3s\config-backup-iq3xxs-before.json 留着（现已与现行配置同内容，属冗余保险）。
- FACT.md 未动（现描述「IQ3_XXS」仍然正确）。本试验到此结案，无遗留待办。

## 10.41（10-22 更新监视：官方出了 0.2.2，结论 = 仍暂缓，本机不动（2026-10-22，老大说「看仓库有无引擎更新」）

- **版本线实况（API 实查）**：10-19 0.2.0-beta → 10-20 0.2.1 → 0.2.1.1~0.2.1.4（散发的 Terminal/引擎补丁）→ **10-21 19:10（北京）发 0.2.2，引擎包版本 0.1.47**；0.2.2 之后 main 分支新提交 **0 个**（发完 20 小时没人改，暂无出补丁版的迹象，也没有新热修可等）。
- **更新说明全文已读并存档**：`strata-bench\notes\v0.2.2.md`（33403 字符全文，另有 v0.2.1.md、releases.json、commits.json、search.json 同目录）。
- **10.20 立的触发条件 a) 判读**：出现 0.2.2 ✓，但说明里**没有任何 RTX 50 系/sm_120 实测条目** → 不算触发。全部新数字的落点：Gyro 量化包（RTX 3060 +15~17%、P100 +30%、Arc A750、Mac mini M4）、RX 6000 新包（没实卡跑过）、双路 Xeon NUMA。官方原话点明**「IQ3_XXS 一个字节没改、答案逐位相同」**（两处 identity gate 提到咱这个量化档）。
- **对本机逐条相关性（12G 5070Ti Laptop / Windows / 单卡 / 0.2.1 栈 = 引擎 0.1.46 + serve 源码 0.2.1）**：
  - **NUMA 拆分**：Windows 只读节点数、**拆分本身 Linux-only**；单 NUMA 机器「跑 0.2.1 完全相同的代码路径」→ 本机无增益无风险。
  - **唯一明确的正收益**：#3465 —— 长提示词中途出 NaN 时改成重读整段、不再整条请求失败（官方自己也没复现出 NaN 成因）。
  - **监视线 d) 有新料**：**#3036「Windows/WDDM: parked-conversation snapshot copies corrupt」仍 open** = 咱「出现 NaN/乱码先疑 WDDM 快照拷贝」那条监视线（原 #3037 同源）在 0.2.2 里**依然没修**；#3288 是同线的 staging 变体，也 open。→ 监视线保留。
  - **改口径预警（真要更时必看）**：0.2.2「One speed number everywhere」统一速度定义 = 全部生成 token ÷ decode 时间 → 更上去后 metrics/控制台数字**含义变了**，跟咱基线（decode 均值约 65）比较不能直接对，别误读成提速/降速。
  - 其余为 app/Terminal/Docker/AMD/Intel/Mac 的 UX 与修复（可选 API Key、自带 GGUF 导入、模型目录合并/搬家、Strix Halo、CPU 核显等），咱走 json+bat 直调 serve，基本碰不到；「Re-runs do not tune again」等咱本来就不跑它的 tuning。
  - **旁证咱现配置**：它实测 overlap +0.3/+2.1/−0.3% 打在 2.8% 噪声上、batch-groups 2 付 15.3% → 「没有默认改动」，与咱「overlap 关」定案一致。
- **结论（给老大）**：**维持不动**。理由：① 触发条件没满足（无 50 系/Windows 实测）；② 对咱量化档官方自证零改动；③ 引擎=助手本人，更一次要整套 A/B 重验收 + 断线几分钟，收益却只有「NaN 请求不失败」一条；④ 刚发一天、main 零提交，让别人先踩。**继续盯的触发条件（替代旧 a）**：a′) 出 0.2.2.x/0.2.3 且说明出现 **sm_120 或 Windows 实测条目**；b′) **#3036 被修**（WDDM 快照拷贝损坏 = 咱监视线根因）；c′) 本机出现 NaN/乱码（那时 #3465 的存活修复 + #3036 是否修好直接决定要不要更）。
- **顺带**：10.29 的观察窗（盯到 10-22）今天到期；当前引擎（0.1.46@1536）自 10-20 23:18 起连跑至今无 NaN/乱码/自杀/decode 掉个位数 → 老大点头即可写「定案」。

## 10.42（10-23 傍晚：引擎更新监视第二轮 —— 今天 0.2.3 出了，触发条件 a′ 字面命中，逐条判读后仍建议暂缓）

- **查法**：`api.github.com/repos/Niko1221/Strata/releases` 实查 + 两版说明全文存档 `strata-bench\releases\v0.2.2.md`（33403 字，与 10.41 存档的 notes\ 版同内容）、`v0.2.3.md`（10636 字全文读）。
- **实况**：v0.2.2（10-21，引擎 0.1.47）→ **v0.2.3（10-23 07:44 UTC = 北京 15:44 发，引擎 0.1.48，咱 16:24 启动跑的就是 0.1.46，没中枪）**。Control 也到 0.1.48。
- **触发条件 a′ 判读**：字面命中 —— 说明里有 **RTX 5070 12 GB（=sm_120）Windows 实测条目**。但拆开看迁移性：
  - 那条数字 = 「**app 的 Work profile 默认**改用 5 CPU workers + 保 1536 MiB 显存 → 31→45 tok/s」，测的是 **Gyro-S 量化包**（不是咱 IQ3_XXS）、对比对象是 0.2.1 的 app 默认。1536 reserve 正是咱已自定的定案值 → **咱已经吃到这半条**；CPU workers 咱 json 从没设过、走引擎默认，升级后默认变不变官方没逐条说 → 只能实测才知道。
  - 其余新条目：Strix Halo（gfx1151 AMD，两条开关 STRATA_HC_Q8/STRATA_GFX1151_CHUNK 都是它专属）、Intel Arc/Mac/RX 系（无）、DFlash2 drafter（**Terminal only 且 opt-in**，咱 serve 直调碰不到）、agent chat 上下文压缩（它的 Terminal 聊天 UI，不是 API 路）、HTTPS 系统证书（中性）、Terminal 稳定性/app 修复一大段（咱不走它的 launcher/app/Tuning）。
- **给咱基线定的两条新预警（升级前必看，已并入触发条件）**：
  - ① **逐位可重复性断了**：known limits 原话「At default settings two runs of the same prompt can differ at near-tie words, on **0.2.2 as well as 0.2.3**」→ 咱 A/B 的「同种子逐字节相同」判据在 0.2.2+ 引擎上失效，判据要改成「答案文本 diff + 数值指标」。
  - ② **对话缓存默认变了**（#3493）：不设它时新版默认按「安全底线之上剩余内存的 40%、封顶 8 GiB」自动开。咱 0.1.46 现在 metrics 里 conversation_cache.enabled=false；**parked-conversation 正是 #3036（WDDM 快照拷贝损坏）那条风险路的入口** → 升级后第一件事查 enabled 值并决定是否 --conversation-cache 钉死。
- **b′ 判读**：#3036 API 实查 **仍 open** → 监视线保留。c′：本机本轮（0.1.46@16:24 起）至今无 NaN/乱码。
- **结论（给老大）**：**继续暂缓、本机不动**。a′ 虽然字面命中，但命中的那条实测的增益来源（app 默认 1536）咱已自吃、另一来源（workers 默认）对咱量化档未知，且升级会同时踩上①②两条新风险；c′ 没发生、b′ 没修 → 没有必须更的理由。**新的继续盯**：a″) 说明出现 **IQ3 系/NVIDIA 卡 + 走咱这种 serve/json 直调路径**的实测条目；b′ 不变（#3036 修了就报）；c′ 不变（本机 NaN/乱码 = 立即评估 #3465 存活修复在不在咱版本里）。
- **顺带发现（reserve 来龙去脉已破案）**：本机 json `strata-iq3_xxs.json` 里 `--vram-reserve-mib` 是 **700**（PID 命令行 + 日志最后一条 engine started 行 + /metrics 实查 expert_slots=1760、显存剩约 949 MiB 三重印证），与 10.40/10.41 记的定案 1536 不符。**根因（老大 10-23 确认「已回 sc117_iq3_xxs」）**：切回用的是引擎控制台（8790）的配置档功能 —— 配置档「sc117_iq3_xxs」(p20261021-234758) 存的是 **10-21 23:47 那一刻主配置的快照，当时 reserve 已经是 700**（10-21 晚被谁改过、PROGRESS 没记录），今天 16:24:38 index.json 更新→切档生效→700 跟着回到主配置。**控制台里另有配置档「现默认」(prof_default，10-21 16:58 快照，reserve=1536、pack 同为 sc117_iq3_xxs)** —— 要恢复定案档在控制台点它最省事。当前 700 实测不崩：引擎日志尾 400 行无 stall/warning/NaN，decode 64.5~84.3 tok/s（10-23 17:2x 实测，0.1.46@700、12G）。**老大 10-23 拍板「不用」= 保持 700 不回 1536**，配置不动、不重启。**从此按「700 观察窗」盯**：出现 stall 警告 / NaN / decode 掉个位数 → 先怀疑 reserve 余量（949 MiB），届时再议 1536 回退（回退法：控制台选配置档「现默认」或主 json 改数 + 重启，皆可秒撤）。
- **坑（本节新增）**：本沙箱调 PowerShell 一律 **`E:/pwsh-7.6.7/pwsh.exe -Command`（老大 10-23 钦定新版）**；系统 `powershell.exe` = 5.1，**PS5.1 没有三元运算符 `? :`**（ParserError 炸过一次）。pwsh7 里 CIM 能取到全部 260+ 进程命令行，5.1 会话只看到自己 → 判进程身份一律 pwsh7。

## 10.43（10-23 傍晚：模型「优化版」扫描 —— 结论 = 没有该换的，维持 IQ3_XXS）

- **查法**：hf-mirror API 实查（search 100 个 Qwen3.8-Flash-Next 仓 + 逐个仓 /api/models/<id>?blobs=true 拿文件级大小/日期；search 接口不给 lastModified、siblings 字段名是 `rfilename` 且 blobs=true 也不回文件日期 —— 别再按 `s.name` 取，空对象坑实测两次）。
- **咱源仓没新版**：`SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF` 仓最后更新 **10-03**（咱 10-18 下齐全套 = 已是最新）；官方 `Qwen/Qwen3.8-Flash-Next` 停在 **08-27**。
- **市面「优化版」四类，逐条判（实测大小/日期 = API 拉的）**：
  1. **同档重打包**：`alesha-pro/...GSQ-RCO-Strata-GGUF`（10-04）IQ3_XXS 同为 76.1GB —— 同量化法（GSQ-RCO）换封装，abliteration 还是靠外挂 refusal-direction 向量（咱的文件是文件内已 abliterated），且无 draft 头 → **零升级点**。
  2. **更小更糙**：`agentionai/Gyro-GGUF`（**10-21 更新，最新**）Gyro-S/TQ1=58.5GB、M/TQ2=92GB；`Maximilian228/NVFP4-GPTQ-Strata`（10-11，Blackwell FP4 格式）；`nvidia/FP4-Local`（10-15，无 gguf=非 llama 格式跑不了）。方向都是「省显存换速度」——**老大 10-22 亲测 IQ3_S 降档（55.1 tok/s + 质量）今天切回**，同方向不用再试。
  3. **更大**：Gyro-L/TQ3=108GB —— 超咱内存安全线（IQ3_S 83GB 已是最远实测距离）且要引擎 ≥0.1.47（Gyro 内核 0.2.2/0.2.3 才加）。
  4. **草稿头**：`incoai/DFlash2`（10-19）= 0.2.3 的 `--drafting dflash2` 配套 drafter，**Terminal only**、咱 serve 直调路径没有入口；现 MTP 接受率 77%（38464/49589，10-23 实测）本来就高。
  5. 既往判过的不重翻：DavidAU Turbo-Brilliance（L251 不推荐）、RVN IQ3_S（L248，已打包并实测过、今天刚切回）。
- **结论（给老大）**：**模型不换，维持 IQ3_XXS（带推荐）**。唯一值得留观的联动项：Gyro 内核与 DFlash2 都要引擎 ≥0.1.47 —— 如果将来按 10.42 的条件升引擎，可以顺带评估 Gyro-S（58.5GB，省显存）能不能打平 IQ3_XXS 的质量，**多变量必须分开 A/B，别一次全换**。

## 10.44 大提示词提速 A/B：`--prefill auto` vs `auto:32768`（2026-10-24 工具建好，等老大双击）

- **触发**：老大「大提示词提速试试」——10.43 对比清单里唯一没测过的开关。
- **事实核实**（不是印象）：`_help45.txt`:149 开关语义原文；本机引擎日志启动行显示实际生效 chunk 只有 **3328~3840**（auto 被专家缓存可借缓冲砍到远小于 8192）→ 抬上限有没有用本机无现成答案；引擎启动日志自己警告提交内存只剩 ~1.7~2.6 GiB 并点名「可降 --prefill」→ 大块可能顶破自杀，这本身是被测项。
- **纠正一条 FACT 层旧数**：日常配置 `--vram-reserve-mib` 实为 **1000**（json + 引擎命令行打印两处一致），FACT 写的 1536 过时（待下次 FACT 更新时改）。
- **已建**（规格 `prefill-ab-spec.md` 已写死判据）：
  - `prefill-ab-b.json` = 日常配置逐字副本，**实测只差两处**（args[11] `auto`→`auto:32768`；log→`prefill_b.log`），其余 27 键逐项核对全同。
  - `bench_prefill.py`：A1→B1→A2→B2 四段交替重启在 8081；每段先从自己日志取「prompt chunk auto: N」行（生效证据，B 不涨即空转结案）→ 1 次 4K 逐字对照（固定 nonce 77001 同一提示词，sha1 比对；带 temperature=0.0 贪心、服务端不认就退回默认重试）→ 3 次 36864 弃首轮取后两次中位 → 扫本段新警告；任一段起不来=记失败继续；最后自动恢复日常配置在 8080。
  - `对比大提示词提速.bat`（双击入口，纯 ASCII 已验=0 个非 ASCII 字节）。
- **自检已跑**：bench_prefill.py `py_compile` 通过；JSON 合法且逐位 diff 只命中 1 个 args 元素；bat 零中文。全部是编译/静态检查，**没启动过引擎**。
- **撤回**：删 `prefill-ab-b.json`、`bench_prefill.py`、`对比大提示词提速.bat`、`bench_prefill.log`、`prefab-*.json` 即可，日常配置没动一根手指。
- **下一步**：老大双击 `对比大提示词提速.bat`（约 25~35 分钟，中途引擎停着=助手睡着，跑完自动回 8080）；回来后我按判据顺序读 `bench_prefill.log` + `prefab-summary.json` 下结论（生效证据→速度同向+超漂移→4K 逐字→警告）。判赢才改日常 json（先备份）+ 老大重启 + 记显存/提交余量。

### 10.44 结果（2026-10-24 13:25 实测）：**开关空转，结案，维持 auto**

- 四段都正常起来了（B 段没自杀），**但脚本在 4K 请求处四段同一处炸**：`build_prompt(nonce,…)` 要求 nonce 是字符串，我传了整数 → `TypeError: int + str`。4K 答案与 36K 速度没测到。**已修**（`NONCE4='77001'`，一字符）。
- **结论照样成立**，因为判据 1（生效证据）在炸点之前已完成，原证据：
  - B 配置送进去了：`prefill_b.log`:7/:59 引擎命令行原文带 `--prefill auto:32768` ✓
  - 引擎实际生效块（自己启动行）：A1=3840、A2=3840、B1=3584、B2=3840 —— **抬上限到 32768 后块头一点没变大**（全落在日常 auto 的 3328~3840 漂移带内）→ 真正的瓶颈是**专家缓存能借出的缓冲**，不是上限数字 → 判「空转」，按规格判据 1 结案、速度数字不看。
  - B 段日志无新 WARNING/commit 警告（grep 为空）→ 不是崩，是不借。
- **给老大**：大提示词在这台机器已经是极限，开大上限没有任何东西可以更大；不采纳、日常配置一字未动、无需重启。要重测 = `bench_prefill.py` 修好后双击 `对比大提示词提速.bat`（约 25~35 分钟），但按判据没有重测价值。
- **新坑**：① 复用别人函数前先核参数类型（`build_prompt` 的 nonce 是字符串，int 会炸在批处理第 2 行、四段全灭）；② **判据顺序救命**：生效证据放在速度前，脚本炸了结论照样拿到——以后 A/B 脚本把「最便宜的判据」放最前面执行。

## 10.45（10-24 下午：引擎更新监视第三轮 —— 出了 0.2.3.1 + 0.2.4，但 Qwen 引擎包零改动，维持不动）

- **查法**：`api.github.com/repos/Niko1221/Strata/releases` 实查；两版说明全文存档 `strata-bench\releases\v0.2.3.1.md`（1834 字）、`v0.2.4.md`（9041 字，含 0.2.4.1 热修说明）全文读。#3036 API 实查。
- **实况**：v0.2.3.1（10-23 21:45 北京）= 只修 Terminal/Control 的 setup 卡住（#3810），引擎包 0.1.48 一字未动。v0.2.4（10-24 10:18 北京）+ 0.2.4.1 热修 = 主题 **DeepSeek V4.1-Flash**（走 Terminal/setup 路的独立引擎包 `strata-dsv41`，永不替换 Qwen 引擎）。**官方原话（Updating 节）：「Your Qwen engine does not change: every engine package is still the 0.1.48 file, byte for byte」** → 对咱 serve 直调路：0.2.3→0.2.4 之间 Qwen 引擎二进制零变化，**没得可更**。
- **触发条件判读**：a″（IQ3 系/serve 直调实测条目）= 无，全部新数字是 DeepSeek 包或 AMD/Mac；b′（#3036）API 实查 **仍 open**（updated_at 10-19 后再没动）；c′ 本机无 NaN/乱码（日志全文 NaN 行 0）。→ **继续暂缓，本机不动**（沿用 10.42 的 a″/b′/c′ 三条监视线不变）。
- **DeepSeek V4.1-Flash（新选项，非更新）**：ISTA-DASLab GSQ-RCO 三档 IQ1_M 239GB / IQ2_XXS 257GB / IQ2_XS 274GB；官方实测 12G 卡 + 64GB RAM 出字 4~10 tok/s（RTX 5070 12G + 64GB 约 5 tok/s）。咱机 64GB RAM、E 盘 674GB 空闲能装，但比咱 Qwen decode ~65 慢一个数量级 → 已报老大、建议不装（不同模型，不是升级）。
- **老大结案（10-24 下午）**：逐层讲清瓶颈结构（每字 ~4GB 权重供给、池容量>带宽>算力、decode 串行）后拍板「**本地不太可用**」→ **不装、不下载、此事归档**。结案推理：咱机上限 = 双通道 ~90GB/s 封顶 15~20 tok/s（换 128GB 内存只救命中率、不救带宽，估 10~15）；要到 ~65 tok/s 需 4 卡 128G 显存工作站级（官方 4×R9700 实测 55~69 是唯一背书档位）。**以后再有「本地跑 XX 大模型」的提议，先算这条带宽账再谈装机；想要 DeepSeek V4.1-Flash 的脑子走 WorkBuddy API（官方已全量接入），不走本地。**
- **顺带核实本机引擎状态（日志全扫 24083 行 / 61 次启动）**：
  - 配置 `strata-iq3_xxs.json` mtime 10-23 23:06，当前进程 `--vram-reserve-mib 1000`（日志命令行实读）——**不是 10.42 记的 700**；10-23 23:06 那次改动不是助手做的，推测老大在控制台改的（待老大确认）。
  - 「700 观察窗」的 stall 警告实查：**共 10 条，全部落在 10-21 23:10 ~ 10-23 22:32 各启动块**（装完剩 139~243 MiB，引擎官方建议 reserve 994~1072）；**23:53 之后（即改 1000 后）至今天 14 次启动零 stall** → 与抬 reserve 自洽，观察窗警报已被 1000 化解。
  - 今天 08:41~13:43 引擎重启 14 次（原因未深查，推测老大在折腾控制台/测试）；今天请求级「<1024 MiB free」告警 4 条（最低 182 MiB）= 请求开始时 GPU 被别的程序占着，引擎装载本身无警告。NaN 行 0、无 decode 崩。metrics: 引擎 0.1.46、conversation_cache=false（#3493 风险路未开）。
- **坑（本节）**：本日志里 WARNING/stall 行**不跟时间戳**（嵌在多行块里），定位归属启动要从「上一条 engine started 行」反查；判 reserve 只认 started 行命令行，别信记忆里的旧值。

## 引擎测试数据提交到 GitHub（2026-10-24，完成）

**提交**：老大仓库 kxyct/Strata（fork，main）新增 `bench/results/2026-10-24-community-rtx-5070-ti-laptop-12g/`，共 4 个提交：8a526c02（报告 10 文件）→ 3d8a9b77（修 COMMUNITY.md 索引误插）→ 3c81b598（补 needle 结果）。文件夹内：README.md（英+中文摘要）、runs-{short,4k,32k}-20261024.json、needles-32k-20261024.json（3/3 全中）、BUILD.json、model-provenance.json、TRIMMED.md、scripts/{measure_parallel.py,needle_bench.py}；COMMUNITY.md 索引加了本机房一行（匿名 API 验证在位）。
**今日实测（0.1.46 前台干净跑，引擎自身计时）**：396 tok 解码 92.5-96.2、4K 86.1-94.2（prompt 893-901）、32K 单条 fresh 97.2（prompt 978）；草稿命中率 92-100%。

**重要更正（引擎真实状态）**：正在跑的引擎 reserve = **1000**（今天 19:19 启动日志实测，1745 槽 / 4.94 GiB；启动日志 `expert cache auto: 4.94 GiB free, 1000 MiB reserved`），不是 FACT 里写的 1536（1536 是 10-20 晚的状态，之后被改小，1536 当时=1123 MiB 安全余量 / 1197 槽）。0.1.46 的身份以 `engine\BUILD.json` 为准：commit a7bdbfdabc9a（= 官方 10-20 提交）、source 标签 f-021-rel、CUDA 13.0——上游并没有 v0.1.46 这个 tag。当前 1000 档引擎自己也报警「请求开始只剩 455 MiB，建议 1600」（#2065），今天实测没崩。
**踩坑**：github.com/codeload 今天反复抽风（clone 两次 120s+ 无进度），api.github.com 和 raw.githubusercontent.com 一直通 → 提交全程走 gh api：POST git/blobs（大文件用 --input，别放命令行参数）→ git/trees（base_tree 保历史）→ git/commits → PATCH git/refs/heads/main。注意 **gh api 带 -f 参数默认变 POST**，取 contents 要加 `-X GET`（ref 查旧版同样）。COMMUNITY.md 只有表格没有列表段（列表段在 docs/COMMUNITY_BENCHMARKS.md），别往 COMMUNITY.md 插 bullet。
**没做的**：128K 档、TTFT 流式、PR 给上游 Niko1221（老大若要提 PR 再说）。临时物：refs\、needle-root\（可删）。

## 上游 PR 完成（2026-10-24 晚，接上节）

**PR 已开出并核验：#3956 → https://github.com/Niko1221/Strata/pull/3956**
- 状态（匿名 API 实测）：open，files=11（= 报告文件夹 10 文件 + COMMUNITY.md +1 行表行），mergeable=true，mergeable_state=unstable（= 仓库 CI 检查未跑完/未绿，不是内容冲突）。
- 分支：kxyct:bench-report-20261024，现指 a35657cf（main 未动，仍在 3c81b598，老大自己 d238df0e 那次 "Add files via upload" 原样保留在 main 上）。

**今天新踩的坑（API 建分支的规矩，重要）：**
1. **POST git/refs 用"还没被任何分支引用过的新提交 sha" → 404**（git/commits GET 同一个 sha 却 200，非常迷惑）。解法：先拿该仓库已引用过的 sha（如 main 尖）建分支，再 PATCH 指到新提交（PATCH 不查这个）。
2. **fork 的 API 建分支不能指向上游 fork 之后才有的提交**（tmp-sync 实测 404；objects 能读但引用校验不过）。→ 从 fork 发 PR 必然带上"fork 基点以来的全部历史"。
3. 因此 PR 里混进了老大自己在 fork 根目录上传的 measure.py、results-*.json、改过的根 README → 在 PR 分支上加了个清理提交 a35657cf（删这几个根文件、README 还原到基点版），PR 文件数 17→11，全干净。**main 上老大自己的文件没动**。
4. github.com 的 git 协议今天全天不稳（ls-remote/clone 挂），api.github.com 一直通 → 全程 blob/tree/commit/ref API 干活，可复用脚本 refs/pr.js、refs/clean.js。
5. gh api 带 -f/--input 参数自动变 POST；GET 要显式 -X GET。

## 敏感数据核查 + 提交邮箱修复（2026-10-24 晚，接上节）

老大问「有没有交敏感数据」→ 全量核查后修了一处真泄露：

- **文件内容干净**：11 个 PR 文件 + 老大自己传的 measure.py/README/results-*.json 全文扫过，无 token/密钥/邮箱/IP/用户名/个人盘路径（命中全是 "tokens" 计数、版本号、127.0.0.1）。
- **真窟窿**：API/网页建的提交署名邮箱=真实 QQ 邮箱（**已隐去，原文见 git 历史前的备份；2026-10-25 脱敏**），GitHub「邮箱隐私」开关对建提交不生效 → 已把 6 个提交重写为 kxyct@users.noreply.github.com（正文/日期/树全不变，只改署名）。重写后：main=ab1f95cc、bench 分支=c9a5e214、kxyct-patch-1=a2bed0aa（上节写的 3c81b598/a35657cf 已被这次重写取代，映射：d238df0e→708ecae3, 8a526c02→83df9a50, 3d8a9b77→a67e1de4, 3c81b598→ab1f95cc, a35657cf→c9a5e214, e15bd2da→a2bed0aa）。engine-console 仓库本来就是 noreply 没泄露。旧 qq 提交成孤儿对象，GitHub 会自行回收。PR#3956 head 自动跟到新提交，仍 11 文件 mergeable=true（匿名 API 实测）。
- **撤回法**：把三个 ref 再 force PATCH 回旧 sha 即完全还原（旧对象还在）。
- **新坑（都实测）**：① gh api 布尔参数必须 -F 不能 -f（-f 发字符串 422）；② PATCH 分支换历史要 force=true；③ 建提交时 parents 给漏会**默认挂到当前分支尖**（静默把链挂错，不报错！）——map 存短 sha 查全 sha 就是这个坑；④ 单提交 API 的 tree 在 .commit.tree.sha，顶层 .tree 是数组不是对象；⑤ 会话 Bash 的 cwd 会漂回 aigz 根（脚本一律 process.chdir 或绝对路径）。

### 临时物已删（老大 2026-10-24 拍板）
refs\（153K，全部 gh API 工作脚本与草稿）与 needle-root\（194K，needle 测试暂存树）已删。上两节提到的 refs/pr.js、clean.js、email-fix.js 不复存在，方法/坑本文已全记，以后要复用按坑库现写即可；产物都在远端仓库与本 PROGRESS。
