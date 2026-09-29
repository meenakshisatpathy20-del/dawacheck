# Data sources

Every figure below is taken from the sources listed in the playbook (researched September 2026). **Re-open each source before quoting it on a slide, and write the year next to the number.**

## Facts used in the pitch

| Stage | Fact | Source (as cited in the playbook) |
|---|---|---|
| Purchase | 52% of 441 farming households bought pesticides on credit; seller trust rated 4.04 / 5 (West Bengal) | Agriculture and Human Values, 2026 |
| Purchase | Spurious pesticides estimated at 25% by value, 30% by volume (**2015**; old figure) | FICCI press release |
| Label | Only 20% of farmers read pesticide labels | Agriculture and Human Values, 2026 |
| Label | Yavatmal warnings were in English and Hindi; most locals speak Marathi | Public Eye, "The Yavatmal scandal" |
| Mixing | Blind mixing named as a cause of the Yavatmal poisonings | Public Eye |
| Spraying | Glove use "nearly nonexistent"; masks rare | Agriculture and Human Values, 2026 |
| Spraying | Yavatmal, Jul to Oct 2017: 20+ deaths, about 800 hospital admissions, hundreds with temporary blindness | Public Eye; NHRC notice (2017) |
| Spraying | 477 pesticides got interim approval for drone use, April 2022 (two years) | DT Next |
| Harvest | FSSAI tested 86,401 food samples (2022–2025); 2.8% exceeded MRL | Punjab Kesari, Aug 2025 |
| Export | EU detections in Indian rice 2015–2025: tricyclazole 97, thiamethoxam 60, carbendazim 20, chlorpyrifos 18 | Lok Sabha answer, Mar 2025 |
| Export | Punjab banned 11 pesticides for basmati from 14 June 2025 | The Tribune |
| Regulation | Insecticides (First Amendment) Rules, 2025: QR with batch, dates, unique ID, licence | QRCodeChimp summary (check the Gazette notification) |
| SOS | AIIMS National Poisons Information Centre: 1800 116 117 | AIIMS NPIC |

## Datasets for the knowledge base

| Dataset | Used for | Where | Status in this repo |
|---|---|---|---|
| CIB&RC "Major Uses of Pesticides" (insecticides, fungicides, herbicides, bio-pesticides, PGRs) | Label claims: crop, pest, dose, water, waiting period | ppqs.gov.in | Parser built and tested; **real PDFs not yet parsed**; seed rows are samples |
| CIB&RC registered products | Is the product registered; registrant; formulation | ppqs.gov.in | Fictional demo catalogue |
| Banned / restricted / refused pesticides | R2 red verdicts | CIB&RC list (Wikipedia summary; verify) | Small hand-made list (endosulfan, phorate, methyl parathion banned; monocrotophos restricted on vegetables): verify |
| State crop-specific bans | R7, MRL Passport | State orders (e.g. Punjab basmati, June 2025) | Punjab's 11 chemicals loaded |
| IRAC / FRAC mode-of-action groups | Cocktail Checker, Rotation Planner | irac-online.org, frac.info | Groups for 31 chemicals |
| EU pesticide MRL database | Export flags | EU Pesticides Database | 4 rice flags from the Lok Sabha answer |
| Toxicity label colours | Safety card | Insecticides Rules, 1971 | Per-product colours in the demo catalogue are placeholders |
| Weather | Spray window | Open-Meteo (free, no key) | Live; simulated mode for the stage |
| Health centres | SOS | OpenStreetMap (Overpass) | Live |
