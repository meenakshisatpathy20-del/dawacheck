# Data sources

Every figure below is taken from the sources linked in the playbook (researched September 2026); the links are the exact ones embedded in the playbook PDF. **Re-open each source before quoting it on a slide, and write the year next to the number.** (The build environment could not reach these sites, so they were not re-checked during the build.)

## Facts used in the pitch

| Stage | Fact | Source |
|---|---|---|
| Purchase | 52% of 441 farming households bought pesticides on credit; seller trust rated 4.04 / 5 (West Bengal) | [Agriculture and Human Values, 2026](https://link.springer.com/10.1007/s10460-026-10852-2) |
| Purchase | Spurious pesticides estimated at 25% by value, 30% by volume (**2015**; old figure) | [FICCI press release](https://ficci.in/public/storage/PressRelease/2124/ficci-press-sep24-chem-study.pdf) |
| Label | Only 20% of farmers read pesticide labels | [Agriculture and Human Values, 2026](https://link.springer.com/10.1007/s10460-026-10852-2) |
| Label | Yavatmal warnings were in English and Hindi; most locals speak Marathi | [Public Eye: The Yavatmal scandal](https://toxicexports.publiceye.ch/) |
| Mixing | Blind mixing named as a cause of the Yavatmal poisonings | [Public Eye](https://toxicexports.publiceye.ch/) |
| Spraying | Glove use "nearly nonexistent"; masks rare | [Agriculture and Human Values, 2026](https://link.springer.com/10.1007/s10460-026-10852-2) |
| Spraying | Yavatmal, Jul to Oct 2017: 20+ deaths, about 800 hospital admissions, hundreds with temporary blindness | [Public Eye](https://toxicexports.publiceye.ch/); [NHRC notice, 9 Oct 2017](https://nhrc.nic.in/media/press-release/nhrc-notices-to-the-centre-government-maharashtra-over-reported-deaths-farmers-due-to-infection-caused-by-spraying-a-pesticide-on-cotton-crops-09-10-2017) |
| Spraying | 477 pesticides got interim approval for drone use, April 2022 (two years) | [DT Next](https://www.dtnext.in/amp/story/news/national/to-fast-track-agri-drone-adoption-centre-approves-477-pesticides); [CIB&RC interim approval notice (18-04-22)](https://www.acfiindia.com/home/central-notice/Interimapprovalforuseofapprovedpesticidewithdronesforcropprotection(18-04-22).pdf) |
| Harvest | FSSAI tested 86,401 food samples (2022–2025); 2.8% exceeded MRL | [Punjab Kesari, Aug 2025](https://english.punjabkesari.com/india/2025/08/07/fssai-tested-86401-food-samples-for-pesticide-residues-28pc-exceeded-limits-govt) |
| Export | EU detections in Indian rice 2015–2025: tricyclazole 97, thiamethoxam 60, carbendazim 20, chlorpyrifos 18 | [Lok Sabha USQ 2057, 11 Mar 2025](https://www.commerce.gov.in/wp-content/uploads/2025/03/LS-USQ-No.2057-dated.-11.03.2025.pdf) |
| Export | Punjab banned 11 pesticides for basmati from 14 June 2025 | [The Tribune](https://www.tribuneindia.com/news/punjab/punjab-government-bans-11-pesticides-for-basmati-crops) |
| Regulation | Insecticides (First Amendment) Rules, 2025: QR with batch, dates, unique ID, licence | [QRCodeChimp summary](https://www.qrcodechimp.com/india-mandates-qr-codes-on-insecticide-labels/) (check the Gazette notification) |
| SOS | AIIMS National Poisons Information Centre: 1800 116 117 | [AIIMS NPIC](https://aiims.edu/index.php/en/npic_intro) |
| Competitors | Farming-app comparison; Bayer Safety Seal; Tagbase; KisanRakshak; CropGuard AI; NPSS | [Khetiyaar 2026](https://www.khetiyaar.com/en/blog/best-ai-farming-apps-india), [Bayer](https://www.bayer.com/en/agriculture/bayer-safety-seal), [Tagbase](https://www.tagbase.io/industries/agrochemicals), [KisanRakshak](https://github.com/Blazikengr8/KisanRakshak), [CropGuard AI](https://imaginecup.microsoft.com/ru-ru/Team/f7c05c49-fa2a-4f48-bf46-f864fb0da753), [NPSS](https://www.clearias.com/national-pest-surveillance-system-npss/) |

## Datasets for the knowledge base

| Dataset | Used for | Where | Status in this repo |
|---|---|---|---|
| CIB&RC "Major Uses of Pesticides" | Label claims: crop, pest, dose, water, waiting period | [Bio-insecticides, as on 31.03.2024](https://ppqs.gov.in/sites/default/files/major_uses_of_pesticides_insecticides_bio_insecticides_as_on_31.03.2024.pdf) and sibling PDFs | Parser built and tested on a synthetic PDF; URL in `pipeline/sources.json`; **real PDFs not yet parsed (site blocked from the build environment)**; seed rows are samples |
| CIB&RC registered products | Is the product registered; registrant; formulation | [PPQS registered products](https://ppqs.gov.in/divisions/cib-rc/registered-products) | Parser built (`pipeline/parse_registry.py`); downloader lists the PDF links found on that page; demo catalogue is fictional until parsed |
| Banned / restricted / refused pesticides | R2 red verdicts | CIB&RC list; [Wikipedia summary](https://en.wikipedia.org/wiki/List_of_banned_and_restricted_pesticides_in_India) (verify against the official PDF) | Parser built; small hand-made list loaded (endosulfan, phorate, methyl parathion, triazophos, dichlorvos banned; monocrotophos restricted on vegetables): verify |
| State crop-specific bans | R7, MRL Passport | State orders (e.g. Punjab basmati, June 2025) | Punjab's 11 chemicals loaded; admins add more in minutes |
| IRAC / FRAC / HRAC mode-of-action groups | Cocktail Checker, Rotation Planner | [IRAC](https://irac-online.org/documents/insecticide-mixtures-and-irm-updated-guidance-irac-statement), frac.info, HRAC | Groups for 84 chemicals |
| EU pesticide MRL database | Export flags | EU Pesticides Database (export CSV) | Importer built (`pipeline/import_eu_mrl.py`); 4 rice flags from the Lok Sabha answer loaded |
| Toxicity label colours | Safety card | [Toxicity label rules](https://en.wikipedia.org/wiki/Toxicity_label) (Insecticides Rules, 1971) | Per-product colours in the demo catalogue are placeholders |
| Weather | Spray window | Open-Meteo (free, no key) | Live; simulated mode for the stage |
| Health centres | SOS | OpenStreetMap (Overpass) | Live |
