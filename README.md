# 港美股机构持股集中度技能 / HK-US Institutional Concentration Skill

一个可复现的 PandaAI 技能，用于分析港股与美股的机构持股结构。  
A reproducible PandaAI skill for analyzing institutional ownership structure across Hong Kong and US equities.

本技能不会简单地把机构持股比例高解释为好或坏，而是从持股广度、头部股东主导程度、集中度、证据质量及源数据异常等维度进行拆解。  
High aggregate ownership is not treated as automatically good or bad; the skill decomposes ownership breadth, top-holder dominance, concentration, evidence quality, and source-data anomalies.

## 核心功能 / Features

- 支持港股、美股、指定股票及全样本运行 / HK, US, selected-symbol, and full-universe support
- 机构总持股比例 / Aggregate institutional ownership
- 前 20 大股东集中度 / Top-20 ownership concentration
- 最大股东持股比例 / Largest-holder percentage
- 股东层面的赫芬达尔指数 / Holder-level Herfindahl-Hirschman Index (HHI)
- 股东排名数据标准化 / Ranked-holder normalization
- 持股结构分类 / Ownership-structure classification
- 证据数量与数据置信度标签 / Evidence-count and confidence labels
- 明确标记缺失数据及异常值 / Explicit missing-data and anomaly states
- 阈值敏感性研究门槛 / Threshold-sensitivity research gate
- 确定性模拟模式与 API 实盘数据模式 / Deterministic mock mode and API-backed live mode
- 自动验收及独立交互式 HTML 报告 / Automated acceptance testing and self-contained interactive HTML reporting

## 指标解读 / Ownership Interpretation

1. `concentration_pct`：整体机构参与程度 / Overall institutional participation
2. `top20_concentration_pct`：最大报告股东群体的持股比例 / Share held by the largest reported group
3. `largest_holder_pct`：单一最大股东的主导程度 / Single-holder dominance
4. `holder_hhi`：排名股东之间的集中程度 / Concentration across ranked holders
5. `ownership_structure`：上述指标的综合结构标签 / Combined structure label
6. `data_confidence`：支持该判断的有效证据程度 / Valid evidence supporting the label

| 标签 / Label | 含义 / Meaning |
|---|---|
| `broad_institutional` | 机构参与度高，但没有明显单一股东主导 / High participation without strong single-holder dominance |
| `dominant_holder` | 大股东或高度集中的排名股东结构占主导 / A large holder or concentrated holder structure dominates |
| `fragmented_or_mixed` | 持股分散或不同指标给出混合信号 / Evidence is dispersed or mixed |
| `data_anomaly` | 一个或多个源指标超出有效解释范围 / Source metrics fall outside valid ranges |
| `insufficient_data` | 证据不足，不应进行高置信度排名 / Evidence is insufficient for confident ranking |

这些标签是透明的筛选规则，并非普适的经济规律。  
These labels are transparent screening rules, not universal economic laws.

## 目录结构 / Repository Structure

```text
skill-hk-us-institutional-concentration/
├── SKILL.md
├── README.md
├── agents/openai.yaml
├── scripts/
│   ├── build_panel.py
│   └── harness.py
├── references/
│   ├── api-map.md
│   └── runtime.md
├── outputs_mock_final/
├── outputs_sample_live/
└── outputs_full/
```

## 环境要求 / Requirements

- Python 3.10+
- `pandas`
- `numpy`
- 实盘 API 模式需要 / Live API mode requires `panda_data>=0.0.9,<0.1`

```bash
pip install "panda_data>=0.0.9,<0.1"
```

## 身份认证与安全 / Authentication & Security

请在仓库外配置环境变量；切勿提交真实凭据、访问令牌、`.env` 文件或私钥。  
Set credentials outside the repository. Never commit credentials, access tokens, `.env` files, or private keys.

```bash
export PANDA_DATA_USERNAME="your_username"
export PANDA_DATA_PASSWORD="your_password"
```

## 使用方法 / Usage

### 模拟数据 / Deterministic Mock Run

```bash
python scripts/build_panel.py --mode mock --market both --output-dir outputs
python scripts/harness.py --output-dir outputs
```

### 指定股票实盘数据 / Selected Live Symbols

```bash
python scripts/build_panel.py \
  --mode api --market both \
  --symbols 0700.HK,0005.HK,AAPL,MSFT \
  --start-date 20250101 --end-date 20251231 \
  --output-dir outputs_live

python scripts/harness.py --output-dir outputs_live
```

### 港美股全样本 / Full HK-US Universe

```bash
python scripts/build_panel.py \
  --mode api --market both --full-universe \
  --output-dir outputs_full

python scripts/harness.py --output-dir outputs_full
```

全样本模式默认跳过规模较大的带日期股东报告；只有确需明细时才添加 `--include-shareholder-reports`。  
Full-universe mode skips the larger dated shareholder-report extract by default; add `--include-shareholder-reports` only when needed.

## 主要产出 / Main Outputs

| 文件 / File | 说明 / Description |
|---|---|
| `institutional_concentration_panel.csv` | 公司层面的广度、主导性、结构及置信度 / Company-level breadth, dominance, structure, and confidence |
| `investor_ranking.csv` | 标准化的股东排名明细 / Normalized ranked-holder detail |
| `shareholder_reports.csv` | 按需生成的带日期股东报告 / Dated shareholder-report detail when requested |
| `raw_*.csv` | 未修改的 API 原始数据 / Unmodified API extracts |
| `quality_report.json` | 覆盖率、缺失值、重复值、异常及警告 / Coverage, missing values, duplicates, anomalies, and warnings |
| `harness_report.json` | 自动验收结果 / Automated acceptance-test result |
| `factor-report.html` | 独立交互式研究报告 / Self-contained interactive research report |

## 全样本参考结果 / Full-Sample Reference Run

- 去重后 9,938 家公司 / 9,938 unique companies after duplicate-key resolution
- 163,179 条标准化股东排名记录 / 163,179 normalized investor-ranking rows
- 机构总持股比例非空覆盖率约 96.4% / Approximately 96.4% non-null aggregate-concentration coverage
- 保留异常源数据并明确标记，而非截断或静默修复 / Source anomalies are labeled rather than clipped or silently repaired

数量取决于数据源覆盖范围和运行日期，未来可能变化。  
Counts depend on source coverage and run date and may change in future releases.

## GitHub 上传说明 / GitHub Upload Notes

本仓库包含全样本原始明细、完整机构持股面板、完整股东排名、小型示例、质量报告及自动验收结果，以支持结果复核和完整复现。`.gitignore` 仅排除本地凭据、密钥、临时输出和系统缓存。  
This repository includes full-universe raw detail, the complete institutional panel and investor ranking, small examples, quality reports, and acceptance-test results for verification and reproducibility. The `.gitignore` excludes only local credentials, keys, ad-hoc outputs, and system caches.

## 研究规范 / Research Safeguards

- 明确市场、股票池、观察日期和股东定义 / Define market, universe, observation date, and holder definition
- 核查接口语义、单位、快照日期及报告日期 / Verify endpoint semantics, units, snapshot dates, and report dates
- 报告返回股票、缺失值、重复值、排名深度及异常 / Report returned symbols, missing values, duplicates, ranking depth, and anomalies
- 综合解读广度、前 20 大占比、最大股东、HHI 及集中度差值 / Interpret breadth, top-20 share, largest holder, HHI, and concentration gap together
- 只比较市场及观察窗口兼容的样本 / Compare only compatible markets and windows
- 至少测试两种主导性或 HHI 阈值 / Test at least two dominance or HHI thresholds
- 只有真实的历史持股快照早于收益期时才允许计算历史 IC 或收益 / Require genuinely dated ownership snapshots before historical IC or return claims
- 区分观察到的结构、经济假设及投资预测 / Separate observed structure, economic hypotheses, and investment predictions

## 历史验证限制 / Historical-Validation Limitation

标准机构集中度接口提供的是当前快照。不得把当前快照向历史日期回填，以人为制造 IC 或收益曲线。  
Standard concentration APIs provide current snapshots; a current snapshot must never be copied backward to manufacture IC or an equity curve.

只有在每个远期收益区间开始前存在真实的带日期持股快照时，历史业绩分析才有效；否则，本技能提供的是严谨的横截面持股诊断，而非伪回测。  
Historical performance analysis is valid only when dated ownership snapshots precede every forward-return period; otherwise, the result is a rigorous cross-sectional diagnosis rather than a pseudo-backtest.

## 局限性 / Limitations

- API 版本可能调整接口或字段名 / API versions may rename endpoints or fields
- 百分比可能使用 0–1 或 0–100 标度，需要标准化 / Percentages may require 0–1 versus 0–100 normalization
- 异常源数据会被保留并标记 / Abnormal source values are retained and labeled
- 股东类别可能混合机构、战略实体及个人 / Holder categories may mix institutions, strategic entities, and individuals
- 港股与美股应在归一化方式及观察窗口一致后再比较 / HK and US results require compatible normalization and observation windows
- 本项目仅用于研究与数据处理，不构成投资建议或自动交易系统 / This project is for research and data processing, not investment advice or an automated trading system

## 许可 / License

公开发布前请添加适用的开源许可证。  
Add the intended open-source license before public distribution.
