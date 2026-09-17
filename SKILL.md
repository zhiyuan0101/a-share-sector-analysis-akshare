---
name: a-share-sector-analysis-akshare
description: A股申万二级行业(124个)板块行情分析，纯 Python + akshare 实现，不依赖任何 MCP 连接器。按周涨幅/月涨幅双维度排行，生成图表与上涨原因分析。只做涨幅榜，不出跌幅榜。触发场景：板块行情、行业涨幅、板块排名、哪些板块涨了、行业轮动、板块分析、sector performance、申万二级。
agent_created: true
---

# A股板块行情分析（akshare 独立版）

对申万二级行业（124 个）做多周期**涨幅**分析，输出双维度涨幅排行、可视化图表与上涨原因解读。

**与 `a-share-sector-analysis` 的区别**：那个依赖 `westock-mcp` 连接器（实时但需用户启用）；本 skill **零 MCP 依赖**，靠 akshare 直连申万宏源研究，随时可跑，代价是数据滞后约 2 个交易日。

**无需用户提供参数**，默认行为：申万二级 + 周涨幅排序 + 月涨幅排序 + 双维度 Top10 上涨原因分析。

**只看涨幅**：本 skill 不生成跌幅榜，不做"最弱方向""资金撤离方向"分析，图表不使用绿色。用户明确要求，2026-09-17。

**直接回复，不落文件**：报告正文一律直接回复在对话里（Markdown 表格 + 短句），**不要生成 HTML / docx / md 报告文件**。用户明确要求，2026-09-17。

---

## 环境准备

只需一个带 akshare 的 Python 3 环境：

```bash
# 已装好时直接验证
python -c "import akshare; print(akshare.__version__)"

# 未安装时（一次性）
pip install akshare
```

后续所有命令用 `PY=python`（**取数用**，需要 akshare）。
`calc_changes.py` 是纯标准库，用任意 Python 3 均可。

> **不要用东方财富接口**（`stock_board_industry_name_em` 等）：在部分网络环境下会被代理拦截，抛 `ProxyError`。申万宏源接口可直连。

> **不要在 Bash 里拼 coreutils 管道**（`ls`/`base64`/`head` 可能全部 not found）。列目录用 Glob，读文件用 Read，写文件用 Write。

---

## 工作流程

### Step 1 · 抓取板块列表与 K 线

```bash
PY=python
"$PY" scripts/fetch_sw2.py --out-dir ./data --workers 6
```

产出：
- `data/sectors.json` — 131 个申万二级行业（含 `上级行业`，可直接映射一级行业）
- `data/kline_data.json` — 每个行业最近 70 根日 K

脚本逻辑：
1. `ak.sw_index_second_info()` 取行业清单（代码形如 `801016.SI`，含 `上级行业` 字段）
2. 6 线程并发调用 `ak.index_hist_sw(symbol=code, period='day')`，失败自动重试 3 次
3. **剔除停更的僵尸指数**——申万已停止发布部分老二级指数（如 801011 林业、801019 农业综合Ⅱ，最后一根 K 线停在 2024 年）。判据：最后一根 K 线日期 < 全体最新日期则丢弃。剔除后正好 **124 个**
4. 元数据里记录 `latestDate`、`droppedStale`、`errorCount`

耗时约 15 秒。

### Step 2 · 计算多周期涨幅并排序

```bash
CALC=python

# 周涨幅（Top 30）
"$CALC" scripts/calc_changes.py --input data/kline_data.json --sector-info data/sectors.json \
  --sort chg_5d  --format tsv --fields name,parent,chg_5d,chg_10d,chg_20d,chg_60d --limit 31

# 月涨幅（Top 30）
"$CALC" scripts/calc_changes.py --input data/kline_data.json --sector-info data/sectors.json \
  --sort chg_20d --format tsv --fields name,parent,chg_20d,chg_5d,chg_10d,chg_60d --limit 31
```

**只用 `--limit`，不要用 `--bottom`**（脚本保留了该参数，但本 skill 不再调用）。

输出字段：`code` `name` `parent` `close` `chg_5d` `chg_10d` `chg_20d` `chg_60d`
（`--limit N` 需 +1 因为第一行是表头。）

口径：`chg_Nd = (最新收盘 - N个交易日前收盘) / N个交易日前收盘`，用交易日而非自然日。
`chg_5d` ≈ 一周，`chg_20d` ≈ 一月，`chg_60d` ≈ 一季（两月）。

**补充统计（必须做）**：脚本自带的 `Up(5d)` 只统计 `--limit` 之后的行数，不能反映全市场广度。要点解读里的「上涨家数 / 占比 / 极差 / 中位数」和「一级行业均值」需要另算全样本，可写一个 20 行左右的小脚本遍历 `kline_data.json`：

- 近 5 日、近 20 日的上涨家数、占比、最大/最小涨幅、极差、中位数
- 按 `parent` 聚合的一级行业均值排行
- 两个窗口各自的起始交易日（用于报告里写明区间）

### Step 3 · 图表

用当前环境里任意可用的图表方案（如 `scripts/render_chart.py` 的 matplotlib 示例，或 ECharts / 前端组件 / 其他内置图表工具）。

**默认直接用内联可视化渲染**（CSS 横向柱状图或内联 SVG）贴进对话回复；**只有在用户明确要求图片文件时**才跑 `render_chart.py` 输出 PNG，并用 `present_files` 单独呈现那一张图。

画**周涨幅 Top 15 横向柱状图**：

- 榜单里全是上涨板块，**柱子统一用红色 `#ef4444`**（A 股红涨惯例），不使用绿色
- 深色主题下：刻度文字 `#E6EDF3`、网格 `rgba(255,255,255,0.07)`
- 柱尾标注数值，不用默认 legend，图例只标"涨幅（红）"

### Step 4 · 检索上涨原因

**周涨幅 Top 10**、**月涨幅 Top 10** 各用 `WebSearch` 检索。
查询模板：`"A股 {板块名} 上涨 原因 {当前年月}"`（涨幅极大的可加 "大涨"/"涨停潮"）。

覆盖四个维度：产业/政策催化、业绩驱动、资金面、商品价格。
注意识别**同源行情**（例如数字媒体/影视院线/出版同属 AI 长剧催化，应在报告里合并归因，不要重复写三遍）。

### Step 5 · 输出分析报告

**报告正文直接回复在对话里**，用 Markdown，**不生成任何报告文件**（HTML/docx/md 都不要）。只有用户明确说"要文件/要文档/导出成 HTML"时才落盘。

按 `references/report-template.md` 的结构组织：

1. 数据说明（截止日、样本数、数据源、滞后提示）——压缩成一两行
2. 周涨幅 Top 30 表格 + 要点解读 + Top10 上涨原因
3. 月涨幅 Top 30 表格 + 要点解读 + Top10 上涨原因
4. 总结：三条主线 + 风险提示 + 免责声明

**排版硬性要求（用户偏好简洁、可扫读，2026-09-17 明确）**：

- 双榜 Top 30 用 **Markdown 表格完整给出**，不要缩成 Top 10
- 上涨原因**每个板块一行短句**（核心逻辑 + 关键数字），不要写成大段散文
- 要点解读、三条主线、风险提示用**紧凑列表**，控制在能快速扫读的长度
- 不要在开头写客套铺垫，直接给结论和表格

---

## 关键注意事项

1. **只看涨幅**：不生成跌幅榜，不做"最弱方向""资金撤离方向"分析；图表柱子统一红色 `#ef4444`，不使用绿色。
2. **直接回复，不落文件**：报告正文一律在对话里输出（Markdown 表格 + 短句）；不要主动生成 HTML 报告。用户明确要求，2026-09-17。
3. **数据滞后 1~2 个交易日**。`index_hist_sw` 返回的 `latestDate` 通常比当前交易日早 1 天，偶尔 2 天；以抓取实际返回的 `latestDate` 为准，必须在报告开头显式声明，并在风险提示里说明最新一两个交易日未纳入。
4. **僵尸指数必须剔除**，否则它们的"最新价"是几个月前的，会严重污染排名。
5. **涨跌幅为 `None`** 表示历史数据不足 N 个交易日，排序时沉底（即使全榜上涨，也不要把 `None` 当成 0%）。
6. **同源归因合并**：申万二级内部高度相关（如光伏设备/电池/风电/电网设备同属新能源），讲原因时要分层到一级行业逻辑，避免碎片化。
7. **广度统计要算全样本**：`calc_changes.py` 输出里的 `Up(5d)` 只覆盖被 `--limit` 截断后的行，不能当作全市场上涨家数。
8. **分析免责**：基于公开市场数据与新闻整理，仅供研究参考，不构成投资建议。
