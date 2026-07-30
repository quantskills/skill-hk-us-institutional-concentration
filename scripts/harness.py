from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="outputs")
    args = p.parse_args()
    root = Path(args.output_dir)
    required = ["institutional_concentration_panel.csv", "investor_ranking.csv",
                "shareholder_reports.csv", "quality_report.json"]
    checks = {"required_files": all((root / x).is_file() for x in required)}
    if checks["required_files"]:
        panel = pd.read_csv(root / required[0])
        quality = json.loads((root / "quality_report.json").read_text(encoding="utf-8"))
        checks.update({
            "nonempty_panel": not panel.empty,
            "required_columns": {"market", "symbol", "concentration_pct",
                                 "top20_concentration_pct", "holder_hhi",
                                 "ownership_structure", "evidence_count",
                                 "data_confidence", "has_data_anomaly"}.issubset(panel.columns),
            "unique_keys": bool(not panel.duplicated(["market", "symbol"]).any()),
            "valid_markets": set(panel["market"]).issubset({"hk", "us"}),
            "concentration_coverage": bool(panel["concentration_pct"].notna().mean() >= 0.90),
            "anomalies_explicit": bool(
                panel.loc[
                    ~panel["concentration_pct"].between(0, 100)
                    & panel["concentration_pct"].notna(),
                    "has_data_anomaly",
                ].all()
            ),
            "valid_structure": set(panel["ownership_structure"]).issubset({
                "dominant_holder", "broad_institutional", "fragmented_or_mixed",
                "data_anomaly", "insufficient_data"}),
            "valid_confidence": set(panel["data_confidence"].dropna()).issubset({
                "low", "medium", "high"}),
            "quality_report_pass": quality.get("status") == "PASS",
        })
    status = "PASS" if checks and all(checks.values()) else "FAIL"
    result = {"status": status, "checks": checks}
    (root / "harness_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
