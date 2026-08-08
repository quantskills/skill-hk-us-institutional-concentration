# Point-in-time and issuer-identity methodology

## ADR and local-share deduplication

Treat an ADR and its local ordinary share as two listings of one economic issuer, not two independent companies. Use the first available stable identifier in this order: `issuer_id`, `company_id`, `entity_id`, then `isin`. When no mapping exists, retain `market:symbol` as a conservative fallback and report the fallback count; never infer an ADR/local relationship from ticker text alone.

For a mapped issuer with multiple listings, retain one row using this priority:

1. explicitly identified primary listing;
2. local ordinary share rather than ADR;
3. row with greater valid evidence coverage;
4. deterministic market and symbol ordering.

Write every removed listing to `issuer_dedup_exclusions.csv` with the reason. Apply the retained-key filter to ranked-holder detail so company and holder outputs remain consistent.

## 13F availability lag

A Form 13F period-end date is not its public availability date. Apply a conservative 45-calendar-day disclosure lag:

```text
availability_date = source_period_end + 45 calendar days
```

Use `availability_date`, never the quarter-end date, for point-in-time joins, IC tests, or forward-return measurement. Keep the original period end and filing type. Other filing types receive zero lag only when the source record itself represents the public filing date; otherwise document the endpoint-specific lag.

