# a-share-sector-analysis-akshare

A股申万二级行业（124 个）板块行情分析技能，纯 Python + [akshare](https://github.com/akfamily/akshare) 实现，**不依赖任何 MCP 连接器**。

## 功能

- 周/月双维度涨跌幅排行（`chg_5d` ≈ 一周、`chg_20d` ≈ 一月、`chg_60d` ≈ 一季，均按交易日计）
- 双维度 Top10 涨跌原因分析
- 生成可视化图表与 Markdown 报告，图表与表格遵循 A 股惯例——**红涨绿跌**

## 安装

把整个目录复制到你所用 Agent 的技能目录（如 Claude Code 的 `~/.claude/skills/`，或其他支持 SKILL.md 约定的技能目录）：

```bash
git clone https://github.com/zhiyuan0101/a-share-sector-analysis-akshare.git
cp -r a-share-sector-analysis-akshare ~/.claude/skills/
```

技能通过 `SKILL.md` 的 frontmatter（`name` / `description`）被自动识别和触发，无需额外注册。

## 依赖

```bash
pip install akshare
```

数据来自申万宏源研究（经 akshare 接口），滞后约 1~2 个交易日（以抓取返回的 `latestDate` 为准）；如需实时数据，请配合行情类 MCP 连接器使用。

## 说明

输出为公开市场数据与新闻的整理结果，仅供研究参考，不构成投资建议。

## License

MIT
