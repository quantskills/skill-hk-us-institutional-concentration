# PandaAI API map

## Hong Kong

- `get_stock_investor_concentration(symbol, fields)`: aggregate investor count, concentration percentage, shares, and holding value.
- `get_stock_top20_concentration(symbol, fields)`: top-20 aggregate concentration.
- `get_stock_investor_ranking(symbol, fields, max_rank)`: ranked holders, names, holding percentages, values, and ranks.
- `get_stock_shareholder_holding(start_date, end_date, symbol, fields)`: dated shareholder reports.

## United States

- `get_stock_investor_centralization(symbol, fields)`: aggregate concentration in SDK 0.0.9. Some task documents call this `get_stock_investor_concentration`.
- `get_stock_top20_centralization(symbol, fields)`: top-20 aggregate concentration in SDK 0.0.9. Some task documents call this `get_stock_top20_concentration`.
- `get_stock_investor_leaderboard(symbol, fields, max_rank)`: ranked holders.
- `get_stock_shareholder_report(start_date, end_date, symbol, fields)`: dated shareholder reports.

## Normalization

API versions may rename columns. Resolve symbols from `symbol`, `ticker`, or `stock_code`; concentration from names containing `concentration`; holder percentage from `holding_pct`, `holdings_pct`, `percentage`, `percent`, or `pct`; holder names from `investor_name`, `holder_name`, `shareholder_name`, or `name`.

Keep missing values as null. Percentages may arrive as either 0–1 or 0–100; convert to 0–100 only when all non-null absolute values are at most 1.
