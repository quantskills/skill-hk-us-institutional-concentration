---
name: skill-hk-us-institutional-concentration
description: Build, compare, and validate institutional ownership structure panels for Hong Kong and US equities with PandaAI investor concentration, ranking, and shareholder-report APIs. Use for ownership breadth, top-holder dominance, HHI, controlling-holder risk, evidence confidence, or within-market institutional ownership screening.
---

# HK-US Institutional Concentration

Build a reproducible company-level ownership panel for Hong Kong and US stocks. Treat
aggregate concentration as an entry point, not a verdict.

## Mandatory research gate

Do not answer immediately when this skill is invoked. Before calculating, ranking,
or interpreting ownership, spend at least 30 seconds on substantive analysis when
the runtime permits. Never satisfy this requirement with an idle sleep.

Complete all checks below before presenting a conclusion. Record each result in
an evidence ledger; a silent assumption does not count as a completed check:

1. Confirm market, universe, observation date, holder definition, and requested use.
2. Verify whether each API value is a current snapshot or historically dated; never backfill a current snapshot into a historical test.
3. Report universe size, non-null coverage, duplicate handling, and source-data anomaly counts.
4. Check percentage scale, HHI range, maximum-holder share, and top-20 consistency.
5. Separate ownership breadth from holder dominance and evidence confidence.
6. Treat `data_anomaly` and `insufficient_data` as non-rankable states, not low-risk observations.
7. If performance validation is requested, require historically dated ownership snapshots and forward returns. Otherwise explain why IC and equity curves are not identified.
8. Test the classification under at least two alternative dominance thresholds
   or HHI cutoffs and identify labels that change.
9. Inspect the largest metric disagreements, such as high aggregate breadth but
   low top-20 ownership, before ranking.
10. Separate observed structure, data confidence, economic interpretation, and
    unsupported return claims.

If any gate fails, state the limitation before showing rankings. Do not use a
visual report or a harness `PASS` to conceal incomplete historical identification.

### Evidence ledger

For research or ranking requests, include a compact ledger with all rows below.
For a single-stock lookup, retain it internally and surface every failure.

| Gate | Required evidence | Failure action |
|---|---|---|
| Scope | market, universe, date, holder definition | state assumptions |
| Semantics | endpoint, units, snapshot/report date | stop historical claim |
| Coverage | returned, missing, duplicates, ranking depth | downgrade confidence |
| Structure | breadth, top-20, largest holder, HHI, gap | do not use one label |
| Anomalies | invalid percentages and HHI | mark non-rankable |
| Sensitivity | two threshold alternatives | label instability |
| Interpretation | evidence vs hypothesis vs prediction | revise conclusion |

## Workflow

1. Normalize symbols: keep Hong Kong symbols as `NNNN.HK`; keep US tickers uppercase.
2. Read [references/api-map.md](references/api-map.md) before changing API calls or field mappings. Read [references/runtime.md](references/runtime.md) when installing the SDK or configuring credentials.
3. Run `scripts/build_panel.py`. Use `--mode mock` for deterministic offline verification and `--mode api` for PandaAI data.
4. Treat the API aggregate concentration value as breadth. Separately compute top-holder dominance and holder HHI from ranking rows.
5. Classify the observed structure as `broad_institutional`, `dominant_holder`, or `fragmented_or_mixed`; do not collapse these states into a single good/bad score.
6. Report `data_confidence` from metric coverage. Preserve raw extracts and never silently convert missing values to zero.
7. Run `scripts/harness.py --output-dir <dir>` and require `PASS` before delivery.

## Commands

```bash
python scripts/build_panel.py --mode mock --market both --output-dir outputs
python scripts/harness.py --output-dir outputs
```

For live data, set the official `PANDA_DATA_USERNAME` and `PANDA_DATA_PASSWORD` variables outside the skill and run:

```bash
python scripts/build_panel.py --mode api --market both --symbols 0700.HK,AAPL --start-date 20250101 --end-date 20251231 --output-dir outputs_live
```

For the complete HK and US universe exposed by PandaData:

```bash
python scripts/build_panel.py --mode api --market both --full-universe --output-dir outputs_full
```

Full-universe mode skips the much larger dated shareholder-report extract by default;
add `--include-shareholder-reports` only when that detail is required.

## Outputs

- `institutional_concentration_panel.csv`: one row per market and symbol, including structure and evidence-confidence labels.
- `investor_ranking.csv`: normalized ranked-holder detail.
- `shareholder_reports.csv`: dated shareholder-report detail when requested.
- `raw_*.csv`: unmodified API extracts.
- `quality_report.json`: row counts, coverage, duplicates, and warnings.
- `harness_report.json`: delivery acceptance result.

## Interpretation

Read the result in layers:

1. `concentration_pct` describes overall institutional participation.
2. `top20_concentration_pct`, `largest_holder_pct`, and `holder_hhi` describe how that participation is distributed.
3. `ownership_structure` summarizes the combination; `data_confidence` says how much evidence supports it.

A high aggregate percentage with low HHI indicates broad institutional ownership;
high HHI or a very large top holder indicates dominance risk. Compare stocks within
the same market and observation date. These are ownership diagnostics, not return
forecasts, and the thresholds are transparent screening rules rather than universal
economic laws.

## Completion gate

Do not call the task complete unless `harness.py` passes, universe and anomaly
counts are reported, every structure label is traceable to visible metrics, the
observation-date limitation is explicit, and any return claim uses genuinely
dated ownership snapshots.
