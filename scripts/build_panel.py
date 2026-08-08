from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build an HK-US ownership concentration panel.")
    p.add_argument("--mode", choices=["mock", "api"], default="mock")
    p.add_argument("--market", choices=["hk", "us", "both"], default="both")
    p.add_argument("--symbols", default="")
    p.add_argument("--full-universe", action="store_true",
                   help="Query every stock exposed by the selected market APIs.")
    p.add_argument("--include-shareholder-reports", action="store_true",
                   help="Also query dated shareholder reports in full-universe mode.")
    p.add_argument("--start-date", default="20250101")
    p.add_argument("--end-date", default="20251231")
    p.add_argument("--max-rank", type=int, default=20)
    p.add_argument("--output-dir", default="outputs")
    return p.parse_args()


def choose_col(df: pd.DataFrame, names: Iterable[str], contains: str | None = None) -> str | None:
    lower = {str(c).lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    if contains:
        for col in df.columns:
            if contains.lower() in str(col).lower():
                return col
    return None


def as_frame(value) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    if isinstance(value, dict):
        for key in ("data", "result", "rows"):
            if key in value:
                return pd.DataFrame(value[key])
    return pd.DataFrame(value)


def selected_symbols(raw: str, market: str) -> list[str]:
    supplied = [x.strip().upper() for x in raw.split(",") if x.strip()]
    defaults = {"hk": ["0700.HK", "0005.HK", "1299.HK"], "us": ["AAPL", "MSFT", "JPM"]}
    values = supplied or defaults[market]
    return [x for x in values if (x.endswith(".HK") if market == "hk" else not x.endswith(".HK"))]


def mock_data(market: str, symbols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = {"hk": [71.8, 66.4, 58.9], "us": [62.1, 73.4, 55.7]}
    conc_rows, top_rows, rank_rows, report_rows = [], [], [], []
    for i, symbol in enumerate(symbols):
        concentration = base[market][i % 3]
        top20 = concentration - (3.0 + i)
        conc_rows.append({"symbol": symbol, "investor_count": 115 + i * 17, "concentration_pct": concentration,
                          "total_holdings": 1_000_000_000 + i * 250_000_000,
                          "total_holdings_value": 4_000_000_000 + i * 700_000_000})
        top_rows.append({"symbol": symbol, "investor_count": 20, "concentration_pct": top20,
                         "holdings": 800_000_000 + i * 100_000_000,
                         "holdings_value": 3_200_000_000 + i * 400_000_000})
        weights = np.array([18, 13, 9, 7, 5], dtype=float) * (1 - i * 0.03)
        for rank, pct in enumerate(weights, 1):
            rank_rows.append({"symbol": symbol, "investor_name": f"{market.upper()} Holder {rank}",
                              "holding_pct": pct, "holdings_value": pct * 10_000_000, "rank": rank})
        report_rows.append({"symbol": symbol, "report_date": "20251231", "holder_name": f"{market.upper()} Holder 1",
                            "holding_pct": weights[0], "currency": "HKD" if market == "hk" else "USD",
                            "filing_type": "13F" if market == "us" else "Shareholder filing"})
    return tuple(map(pd.DataFrame, (conc_rows, top_rows, rank_rows, report_rows)))


def init_api():
    try:
        import panda_data
    except ImportError as exc:
        raise RuntimeError("panda_data is unavailable; install/configure it or use --mode mock") from exc
    username = os.getenv("PANDA_DATA_USERNAME") or os.getenv("PANDA_USERNAME")
    password = os.getenv("PANDA_DATA_PASSWORD") or os.getenv("PANDA_PASSWORD")
    if username and password:
        kwargs = {"username": username, "password": password}
        base_url = os.getenv("PANDA_DATA_BASE_URL") or os.getenv("PANDA_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url
        panda_data.init_token(**kwargs)
    elif hasattr(panda_data, "init"):
        panda_data.init()
    else:
        raise RuntimeError("Set PANDA_DATA_USERNAME and PANDA_DATA_PASSWORD for PandaData authentication")
    return panda_data


def api_data(api, market: str, symbols: list[str], start: str, end: str, max_rank: int,
             include_reports: bool = True):
    query = symbols if symbols else ""
    if market == "hk":
        concentration = as_frame(api.get_stock_investor_concentration(symbol=query, fields=[]))
        top20 = as_frame(api.get_stock_top20_concentration(symbol=query, fields=[]))
        ranking = as_frame(api.get_stock_investor_ranking(symbol=query, fields=[], max_rank=max_rank))
        reports = as_frame(api.get_stock_shareholder_holding(
            symbol=query, fields=[], start_date=start, end_date=end)) if include_reports else pd.DataFrame()
    else:
        concentration_func = getattr(api, "get_stock_investor_centralization",
                                     api.get_stock_investor_concentration)
        top20_func = getattr(api, "get_stock_top20_centralization",
                            api.get_stock_top20_concentration)
        concentration = as_frame(concentration_func(symbol=query, fields=[]))
        top20 = as_frame(top20_func(symbol=query, fields=[]))
        ranking = as_frame(api.get_stock_investor_leaderboard(symbol=query, fields=[], max_rank=max_rank))
        reports = as_frame(api.get_stock_shareholder_report(
            symbol=query, fields=[], start_date=start, end_date=end)) if include_reports else pd.DataFrame()
    return concentration, top20, ranking, reports


def normalize_pct(series: pd.Series) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce")
    if out.notna().any() and out.abs().max() <= 1:
        out *= 100
    return out


def add_issuer_identity(panel: pd.DataFrame, source: pd.DataFrame, market: str) -> pd.DataFrame:
    """Attach issuer identity so ADRs and local shares are not counted twice.

    Prefer stable vendor identifiers. Fall back to market:symbol when the source
    provides no issuer mapping; the fallback is deliberately conservative and
    never guesses that two listings represent the same issuer.
    """
    source = source.copy()
    symbol_col = choose_col(source, ["symbol", "ticker", "stock_code"])
    if symbol_col is None:
        panel["issuer_key"] = market + ":" + panel["symbol"]
        panel["listing_type"] = "unknown"
        panel["is_primary_listing"] = pd.NA
        return panel
    source["symbol"] = source[symbol_col].astype(str).str.upper()
    issuer_col = choose_col(source, ["issuer_id", "company_id", "entity_id", "isin"])
    type_col = choose_col(source, ["security_type", "listing_type", "instrument_type"])
    adr_col = choose_col(source, ["is_adr", "adr_flag"])
    primary_col = choose_col(source, ["is_primary_listing", "primary_listing", "is_primary"])
    meta = source.drop_duplicates("symbol", keep="first").set_index("symbol")
    if issuer_col:
        issuer = meta[issuer_col].astype("string").str.strip()
        issuer = issuer.where(issuer.notna() & issuer.ne(""))
        panel["issuer_key"] = panel["symbol"].map(issuer)
    else:
        panel["issuer_key"] = pd.NA
    panel["issuer_key"] = panel["issuer_key"].fillna(market + ":" + panel["symbol"])
    if type_col:
        panel["listing_type"] = panel["symbol"].map(meta[type_col]).astype("string").str.lower()
    elif adr_col:
        adr = panel["symbol"].map(meta[adr_col]).astype("boolean")
        panel["listing_type"] = np.where(adr.fillna(False), "adr", "local")
    else:
        panel["listing_type"] = "unknown"
    panel["is_primary_listing"] = (
        panel["symbol"].map(meta[primary_col]).astype("boolean") if primary_col else pd.NA
    )
    return panel


def deduplicate_issuers(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep one economically representative listing for each mapped issuer."""
    if panel.empty:
        return panel, pd.DataFrame()
    work = panel.copy()
    work["_primary_priority"] = work["is_primary_listing"].astype("boolean").fillna(False).astype(int)
    work["_local_priority"] = ~work["listing_type"].fillna("unknown").str.contains("adr", case=False)
    work["_evidence_priority"] = pd.to_numeric(work["evidence_count"], errors="coerce").fillna(-1)
    work = work.sort_values(
        ["issuer_key", "_primary_priority", "_local_priority", "_evidence_priority", "market", "symbol"],
        ascending=[True, False, False, False, True, True],
    )
    duplicate_issuer = work.duplicated("issuer_key", keep=False)
    excluded = work.loc[duplicate_issuer & work.duplicated("issuer_key", keep="first")].copy()
    excluded["exclusion_reason"] = "ADR/local duplicate; retained primary or local listing"
    kept = work.drop_duplicates("issuer_key", keep="first").copy()
    cleanup = ["_primary_priority", "_local_priority", "_evidence_priority"]
    return kept.drop(columns=cleanup), excluded.drop(columns=cleanup)


def normalize_report_timing(report: pd.DataFrame, market: str) -> pd.DataFrame:
    """Add information-availability dates; US 13F data becomes usable after 45 days."""
    report = report.copy()
    if report.empty:
        for col in ("market", "source_period_end", "availability_date", "disclosure_lag_days",
                    "point_in_time_eligible"):
            report[col] = pd.Series(dtype="object")
        return report
    report.insert(0, "market", market)
    date_col = choose_col(report, ["holding_date", "report_date", "period_end", "date"])
    filing_col = choose_col(report, ["filing_type", "report_type", "form_type"])
    source_date = pd.to_datetime(report[date_col].astype(str), errors="coerce") if date_col else pd.NaT
    filing = report[filing_col].astype("string") if filing_col else pd.Series("", index=report.index)
    is_13f = filing.str.contains("13F", case=False, na=False) & market.eq("us") if isinstance(market, pd.Series) else filing.str.contains("13F", case=False, na=False) & (market == "us")
    lag = np.where(is_13f, 45, 0)
    report["source_period_end"] = source_date
    report["disclosure_lag_days"] = lag
    report["availability_date"] = source_date + pd.to_timedelta(lag, unit="D")
    report["point_in_time_eligible"] = report["availability_date"].notna()
    return report


def normalize(market: str, concentration: pd.DataFrame, top20: pd.DataFrame,
              ranking: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    def symbolized(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        col = choose_col(df, ["symbol", "ticker", "stock_code"])
        if col is None:
            raise ValueError("API result has no symbol column")
        df["symbol"] = df[col].astype(str).str.upper()
        return df

    concentration, top20, ranking = map(symbolized, (concentration, top20, ranking))
    concentration = concentration.drop_duplicates("symbol", keep="first")
    top20 = top20.drop_duplicates("symbol", keep="first")
    c_col = choose_col(concentration, [
        "concentration_pct", "concentration_percentage", "investor_outstanding_ratio"], "concentration")
    t_col = choose_col(top20, [
        "top20_concentration_pct", "concentration_pct", "investor_outstanding_ratio"], "concentration")
    h_col = choose_col(ranking, [
        "holding_pct", "holdings_pct", "investor_outstanding_ratio", "percentage", "percent", "pct"], "pct")
    n_col = choose_col(ranking, ["investor_name", "holder_name", "shareholder_name", "name"])
    r_col = choose_col(ranking, ["rank", "ranking"])
    normalized_rank = pd.DataFrame({"market": market, "symbol": ranking["symbol"]})
    normalized_rank["holder_name"] = ranking[n_col] if n_col else pd.NA
    normalized_rank["holding_pct"] = normalize_pct(ranking[h_col]) if h_col else np.nan
    normalized_rank["rank"] = pd.to_numeric(ranking[r_col], errors="coerce") if r_col else np.nan
    stats = normalized_rank.groupby("symbol", as_index=False).agg(
        holder_hhi=("holding_pct", lambda x: float(np.square(x.dropna() / 100).sum()) if x.notna().any() else np.nan),
        largest_holder_pct=("holding_pct", "max"),
        ranked_holder_count=("holder_name", "count"),
    )
    panel = pd.DataFrame({"symbol": concentration["symbol"]})
    panel["market"] = market
    panel["concentration_pct"] = normalize_pct(concentration[c_col]) if c_col else np.nan
    top_map = pd.Series(normalize_pct(top20[t_col]).values, index=top20["symbol"]).to_dict() if t_col else {}
    panel["top20_concentration_pct"] = panel["symbol"].map(top_map)
    panel = panel.merge(stats, on="symbol", how="left")
    panel["concentration_gap_pct"] = panel["concentration_pct"] - panel["top20_concentration_pct"]
    # Concentration is not one-dimensional: the same aggregate percentage can
    # represent broad institutional participation or one-holder dominance.
    valid_concentration = panel["concentration_pct"].between(0, 100)
    valid_top20 = panel["top20_concentration_pct"].between(0, 100)
    valid_hhi = panel["holder_hhi"].between(0, 1)
    valid_largest = panel["largest_holder_pct"].between(0, 100)
    panel["has_data_anomaly"] = (
        panel["concentration_pct"].notna() & ~valid_concentration
        | panel["top20_concentration_pct"].notna() & ~valid_top20
        | panel["holder_hhi"].notna() & ~valid_hhi
        | panel["largest_holder_pct"].notna() & ~valid_largest
    )
    dominance = (
        (panel["largest_holder_pct"] >= 20)
        | (panel["holder_hhi"] >= 0.10)
    )
    broad = (
        (panel["concentration_pct"] >= 50)
        & (panel["largest_holder_pct"] < 20)
        & (panel["holder_hhi"] < 0.10)
    )
    panel["ownership_structure"] = np.select(
        [
            panel["has_data_anomaly"],
            panel["concentration_pct"].isna(),
            dominance,
            broad,
        ],
        [
            "data_anomaly",
            "insufficient_data",
            "dominant_holder",
            "broad_institutional",
        ],
        default="fragmented_or_mixed",
    )
    evidence_count = pd.concat(
        [valid_concentration, valid_top20, valid_hhi, valid_largest], axis=1
    ).sum(axis=1)
    panel["evidence_count"] = evidence_count
    panel["data_confidence"] = pd.cut(
        evidence_count, bins=[-1, 1, 3, 4], labels=["low", "medium", "high"]
    )
    panel = add_issuer_identity(panel, concentration, market)
    return panel, normalized_rank.sort_values(["symbol", "rank"], na_position="last")


def main() -> None:
    args = parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    markets = ["hk", "us"] if args.market == "both" else [args.market]
    api = init_api() if args.mode == "api" else None
    panels, rankings, reports = [], [], []
    warnings = []
    for market in markets:
        symbols = [] if args.full_universe else selected_symbols(args.symbols, market)
        if not symbols and not args.full_universe:
            warnings.append(f"No {market.upper()} symbols selected")
            continue
        include_reports = not args.full_universe or args.include_shareholder_reports
        raw = api_data(
            api, market, symbols, args.start_date, args.end_date, args.max_rank,
            include_reports=include_reports,
        ) if api else mock_data(market, symbols)
        if args.full_universe and not include_reports:
            warnings.append(
                f"Skipped {market.upper()} shareholder reports in full-universe mode; "
                "use --include-shareholder-reports to request them."
            )
        concentration, top20, ranking, report = raw
        for label, frame in zip(("concentration", "top20", "ranking", "shareholder_report"), raw):
            frame.to_csv(out / f"raw_{market}_{label}.csv", index=False, encoding="utf-8-sig")
        panel, normalized_rank = normalize(market, concentration, top20, ranking)
        panels.append(panel)
        rankings.append(normalized_rank)
        reports.append(normalize_report_timing(report, market))
    panel = pd.concat(panels, ignore_index=True) if panels else pd.DataFrame()
    ranking = pd.concat(rankings, ignore_index=True) if rankings else pd.DataFrame()
    report = pd.concat(reports, ignore_index=True) if reports else pd.DataFrame()
    panel, issuer_exclusions = deduplicate_issuers(panel)
    if not ranking.empty and not panel.empty:
        kept_keys = pd.MultiIndex.from_frame(panel[["market", "symbol"]])
        ranking_keys = pd.MultiIndex.from_frame(ranking[["market", "symbol"]])
        ranking = ranking.loc[ranking_keys.isin(kept_keys)].copy()
    panel.to_csv(out / "institutional_concentration_panel.csv", index=False, encoding="utf-8-sig")
    ranking.to_csv(out / "investor_ranking.csv", index=False, encoding="utf-8-sig")
    report.to_csv(out / "shareholder_reports.csv", index=False, encoding="utf-8-sig")
    issuer_exclusions.to_csv(out / "issuer_dedup_exclusions.csv", index=False, encoding="utf-8-sig")
    quality = {
        "status": "PASS" if not panel.empty and not panel.duplicated(["market", "symbol"]).any() else "FAIL",
        "mode": args.mode, "panel_rows": len(panel), "ranking_rows": len(ranking),
        "missing_concentration": int(panel.get("concentration_pct", pd.Series(dtype=float)).isna().sum()),
        "data_anomaly_rows": int(panel.get("has_data_anomaly", pd.Series(dtype=bool)).sum()),
        "duplicate_keys": int(panel.duplicated(["market", "symbol"]).sum()) if not panel.empty else 0,
        "duplicate_issuers_excluded": int(len(issuer_exclusions)),
        "issuer_identity_fallback_rows": int(panel["issuer_key"].str.contains(":", regex=False).sum()) if not panel.empty else 0,
        "thirteen_f_rows": int((report.get("disclosure_lag_days", pd.Series(dtype=float)) == 45).sum()),
        "thirteen_f_lag_days": 45,
        "warnings": warnings,
        "sdk_version": importlib.metadata.version("panda_data") if args.mode == "api" else None,
        "markets": markets,
        "symbol_count": int(panel["symbol"].nunique()) if not panel.empty else 0,
        "symbols_preview": panel["symbol"].head(20).tolist() if not panel.empty else [],
    }
    (out / "quality_report.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    main()
