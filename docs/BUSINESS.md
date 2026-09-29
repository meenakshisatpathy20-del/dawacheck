# Business model, go-to-market and impact (playbook section 17)

Farmers never pay; four institutional customers do, each for something they already need.
**Prices are placeholders to validate with real conversations, not researched figures.**

| Customer | Pain | What they get (built) | How to charge (to validate) |
|---|---|---|---|
| Exporters and FPOs | Residue rejections, no spray records from farmers | MRL Passport for every member plot; FPO export view with residue flags and earliest safe harvest per plot (`/app/officer/export`) | Per farmer per season, or per consignment |
| Agrochemical brands | Counterfeits damage sales and trust | Map of cloned QR codes and suspicious batches of their brands (Fake-Batch Radar) | Annual data subscription |
| State agriculture departments | Few inspectors, no early signal of fake inputs | Fake-Batch Radar, batch timelines with shops, farmer reports with photos; officers confirm reports after inspection | Annual licence or grant-funded pilot |
| Dealers | Farmers doubt them; competition from online sellers | "DawaCheck Verified Dealer" badge (roadmap: needs scan volume first) | Small monthly fee |

## Go-to-market
1. **Pilot:** one FPO growing basmati or cotton; 200 farmers; one season. Measure scans per farmer, red/yellow share, money saved, spray-log completeness.
2. **Proof for government:** share the pilot's Radar data with the district agriculture officer.
3. **Scale through institutions:** FPO federations, state agriculture departments, KVKs; bundle with existing extension programmes.
4. **Moat:** the cleaned knowledge base plus crowd-sourced batch and price data grow with every scan; competitors would have to rebuild both.

## Impact metrics to report (all live at `GET /metrics` and the dashboard's Impact tab)
| Metric | Field |
|---|---|
| Scans done and share of red/yellow verdicts | `scans`, `red_share`, `yellow_share` |
| Money saved per farmer from Bill Scan | `money_saved_rs`, `money_saved_per_farmer_rs` |
| Sprays logged with a safe harvest date | `sprays_logged`, `sprays_with_safe_date` |
| Suspicious batches flagged and confirmed by officers | `suspicious_batches_flagged`, `reports_confirmed_by_officers` |
| Consignments sold with an MRL Passport | proxy: `plots_with_passport`, `passport_views_by_buyers` (opens of the public passport page). Record actual consignments with the FPO during the pilot. |
