# PropTech: Minimal Real‑Estate Data Model → Loaders → Trivial Features (with Inference TODOs)

A small, production‑friendly scaffold for building a **property “source‑of‑truth”** and generating lender‑ and investor‑grade outputs. It encodes the physical/legal chain

**Parcel → Building → Unit → Lease → Meter/IoT → Permit → Title**

as Python dataclasses; loads those facts from Postgres/PostGIS; computes **15 families of trivial (algebraic) metrics**; and leaves clear **TODO(Inference)** hooks for models you’ll add later (AVM, PD/LGD, CPR/CDR, rent recs, etc.).

---

## TL;DR

- **This repo gives you:**
  1) a clean **data model** and SQL schema,  
  2) a **loader** that returns typed Python objects,  
  3) a library of **trivial features** (pure algebra/joins),  
  4) a CLI to run an **end‑to‑end demo** for any unit UUID.

- **You add later:** inference models where comments say `# TODO Inference`.

---

## Why this structure

Real estate has a **vertical moat** (shape, place, title, permits, leases, meters) that FinTech rails don’t capture. The winning system fuses **property truth** with **financial rails**. This scaffold helps you own the property model and plug it into lending/securitization/reporting.

---

## Repository layout

```
proptech/
  __init__.py
  models.py        # dataclasses + low-level helpers (stable domain truth)
  features.py      # 15 families of trivial metrics + TODO(Inference) comments
  db.py            # SQLAlchemy loader + row→dataclass mappers
  cli.py           # CLI: pull a unit chain and print computed outputs (JSON)
sql/
  schema.sql       # Postgres/PostGIS DDL + view (v_unit_core)
pyproject.toml
.env.example
README.md
```

---

## Data model (minimal facts)

- **Parcel**: `id, muni_id, zoning, geom_wkt (polygon)`  
- **Building**: `id, parcel_id, year_built, structure, floors, bua_m2`  
- **Unit**: `id, building_id, use_type, nla_m2, floor_no, [bedrooms], [orientation]`  
- **Lease**: `id, unit_id, tenant_hash, start_date, end_date, rent_monthly, deposit, status`  
- **Meter**: `id, scope('building'|'unit'), scope_id, type, provider_acct`  
- **MeterReading**: `meter_id, ts, value`  
- **Permit**: `id, scope, scope_id, kind, status, issued_on, completed_on, permit_no`  
- **TitleRecord**: `id, scope('parcel'|'unit'), scope_id, owner_hash, deed_no, encumbrance{...}, effective_on`

> **Geometry**: store parcel boundary in PostGIS (`GEOMETRY(POLYGON, 4326)`), export as WKT into Python.

---

## What’s in `sql/schema.sql`

- Tables for the eight entities above.  
- A **view** `v_unit_core` that joins `unit` → `building` → `parcel` and returns one row per unit with parcel WKT, zoning, year_built, etc. That view is the fast path to load a **unit chain** in one round‑trip.

---

## Install & run

### Prereqs
- Python **3.10+**  
- Postgres **13+** with **PostGIS 3+** (for the `geom` column)

### Setup

```bash
# 1) Create and activate a virtualenv
python -m venv .venv
source .venv/bin/activate

# 2) Install deps
pip install -U pip
pip install SQLAlchemy psycopg2-binary python-dotenv

# 3) Create your DB schema (uses PostGIS)
# Set DATABASE_URL or pass it inline to psql
psql "$DATABASE_URL" -f sql/schema.sql

# 4) Configure database URL (copy and edit)
cp .env.example .env
# .env contains: DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/propdb
export $(grep -v '^#' .env | xargs)
```

---

## Quickstart: populate some rows (example)

```sql
-- Example insert (replace UUIDs and WKT with real ones)
INSERT INTO parcel (id, muni_id, zoning, geom)
VALUES ('00000000-0000-0000-0000-0000000000a1', 'JED-112233', 'R3',
        ST_GeomFromText('POLYGON((39.165 21.571, 39.166 21.571, 39.166 21.572, 39.165 21.572, 39.165 21.571))', 4326));

INSERT INTO building (id, parcel_id, year_built, structure, floors, bua_m2)
VALUES ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000a1', 2016, 'RC frame', 12, 14800);

INSERT INTO unit (id, building_id, use_type, nla_m2, floor_no, bedrooms, orientation)
VALUES ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1',
        'residential_flat', 128.0, 9, 3, 'SW');

INSERT INTO lease (id, unit_id, tenant_hash, start_date, end_date, rent_monthly, deposit, status)
VALUES ('00000000-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-0000000000c1',
        'th:ab12', '2025-02-01', '2026-01-31', 5200.00, 5200.00, 'active');

INSERT INTO permit (id, scope, scope_id, kind, status, issued_on, completed_on, permit_no)
VALUES ('00000000-0000-0000-0000-0000000000e1', 'building', '00000000-0000-0000-0000-0000000000b1',
        'occupancy', 'completed', '2016-09-03', '2016-10-12', 'JED-OCC-2016-9981');

INSERT INTO title_record (id, scope, scope_id, owner_hash, deed_no, encumbrance_json, effective_on)
VALUES ('00000000-0000-0000-0000-0000000000f1', 'unit', '00000000-0000-0000-0000-0000000000c1',
        'oh:9f', 'JED-TD-2023-55421', '{"lien_status":"free"}', '2023-11-18');

-- Optional: electricity meter + daily readings...
```

---

## Run the CLI (end‑to‑end)

```bash
python -m proptech.cli \
  --unit-id 00000000-0000-0000-0000-0000000000c1 \
  --days-back 7 \
  --assumed-cap-rate 0.06 \
  --loan-balance 650000
```

**Sample output (trimmed):**
```json
{
  "parcel": {"zoning": "R3", "muni_id": "JED-112233"},
  "building": {"age_years": 9, "floors": 12, "bua_m2": 14800.0},
  "unit": {"use_type": "residential_flat", "nla_m2": 128.0, "floor_no": 9},
  "leases": {"active_count": 1, "rent_monthly_total": 5200.0},
  "valuation": {
    "assumed_cap_rate": 0.06,
    "noi_annual": 62400.0,
    "implied_value": 1040000.0,
    "ltv_from_input_balance": 0.625
  },
  "compliance": {"days_since_occupancy": 3250, "title_clean": true},
  "energy": {"kwh_per_m2_day": 0.0, "window_days": 7},
  "_meta": {"generated_on": "2025-08-31"}
}
```

---

## What’s in each Python module

### `proptech/models.py`
- Dataclasses for **Parcel / Building / Unit / Lease / Meter / MeterReading / Permit / TitleRecord**  
- Light helpers: `building_age_years()`, `title_clean_flag_from_record()`

### `proptech/db.py`
- SQLAlchemy engine (`DATABASE_URL` from `.env`)  
- Fetchers:
  - `fetch_unit_core(unit_id)` → `(Unit, Building, Parcel)`
  - `fetch_active_leases(unit_id)` → `[Lease]`
  - `fetch_latest_permit_for_building(building_id)` → `Permit | None`
  - `fetch_latest_title(unit_id, parcel_id)` → `TitleRecord | None`
  - `fetch_unit_meters(unit_id)` → `[Meter]`
  - `fetch_readings(meter_id, days_back=30)` → `[MeterReading]`

### `proptech/features.py`
The **15 families** of trivial metrics as pure functions (+ `# TODO Inference` comments). Function examples:

- Valuation: `noi`, `cap_rate`, `value_from_cap`, `dscr`, `yield_on_cost`, `equity_multiple`  
- Lending: `ltv`, `cltv`, `dti`, `residual_income`  
- Capital‑markets: `tape_qc_flags`, `weighted_average_life`  
- Leasing: `rent_roll_total`, `occupancy_rate`, `avg_time_to_lease`  
- Ops/CapEx: `kwh_per_m2_day_from_series`, `mttr`, `opex_per_unit`  
- Compliance: `days_since_last_occupancy`, `zoning_mismatch`, `title_clean_flag_from_record`  
- ESG: `carbon_intensity_kgco2e_per_m2_year`, `water_intensity_m3_per_m2_year`  
- Market: `neighborhood_median_rent`, `supply_count`, `turnover_rate`  
- Development: `far`, `coverage_ratio`, `parking_ratio`  
- Insurance: `sum_insured_from_replacement_cost`, `deductible_effect_expected_cost`  
- Fraud/Governance: `area_sanity_flag`, `occupancy_vs_usage_flag`  
- Tenant: `avg_satisfaction`, `amenity_utilization`, `cohort_churn_rate`  
- Portfolio: `exposure_by_bucket`, `weighted_yield`, `simple_risk_parity_weights`  
- Islamic finance: `murabaha_equal_installments_schedule`, `ijara_monthly_rent`  
- Reporting: `los_package_dict(...)`

### `proptech/cli.py`
- Orchestrates a run: loads a unit chain, calls trivial metrics, prints JSON.  
- Flags:
  - `--unit-id UUID` (required)  
  - `--days-back N` (meter window)  
  - `--assumed-cap-rate FLOAT`  
  - `--loan-balance FLOAT`

---

## Feature families: trivial vs inference

| # | Family | Trivial outputs (in code) | Inference (left as `# TODO`) |
|---|--------|---------------------------|-------------------------------|
| 1 | Valuation | `noi`, `cap_rate`, `value_from_cap`, `dscr`, `yield_on_cost`, `equity_multiple` | AVM fair value; IRR/NPV w/ stochastic vacancies; market cap‑rate; obsolescence score |
| 2 | Lending | `ltv`, `cltv`, `dti`, `residual_income` | PD/LGD/EAD; income stability; forward LTV via HPI |
| 3 | Capital‑mkts | `tape_qc_flags`, `weighted_average_life` | CPR/CDR/Severity models; waterfall & trigger scenarios; pool correlation |
| 4 | Leasing | `rent_roll_total`, `occupancy_rate`, `avg_time_to_lease` | Market rent recs; renewal/churn; concession optimization |
| 5 | Ops/CapEx | `kwh_per_m2_day_from_series`, `mttr`, `opex_per_unit` | Predictive failure; normalized Opex; retrofit timing |
| 6 | Compliance | `days_since_last_occupancy`, `title_clean_flag_from_record`, `zoning_mismatch` | Composite compliance risk; permit delay probability |
| 7 | ESG | `carbon_intensity_kgco2e_per_m2_year`, `water_intensity_m3_per_m2_year`, hazard distance score | Retrofit savings; resilience index; IAQ comfort |
| 8 | Market | `neighborhood_median_rent`, `supply_count`, `turnover_rate` | Hedonic/time‑adjusted comps; micro‑location score; trend detection |
| 9 | Dev/Site | `far`, `coverage_ratio`, `parking_ratio` | Highest & best use; absorption & mix optimization; critical‑path delays |
|10 | Insurance | Sum insured; deductible effect | Peril loss curves; premium optimization; BI exposure |
|11 | Fraud/Gov | Area sanity; occupancy‑vs‑usage | Synthetic identities; inconsistency scoring; data lineage quality |
|12 | Tenant | Avg satisfaction; amenity utilization; cohort churn | Churn drivers; amenity pricing; sentiment from text |
|13 | Portfolio | Exposure by bucket; weighted yield; simple risk parity | Efficient frontier; factor exposures; hedge sizing |
|14 | Islamic | Murabaha schedule; Ijara rent proxy | Sharia evidence scoring; profit‑rate sensitivity; residual value risk |
|15 | Reports | `los_package_dict` | Redaction policies; anomaly‑aware reporting; confidence weights |

---

## Data inventory checklist (what you actually need to collect)

**Tier‑0 (must‑have):**
- Parcel: `id, muni_id, zoning, geom`  
- Building: `id, parcel_id, year_built, structure, floors, bua_m2`  
- Unit: `id, building_id, use_type, nla_m2, floor_no, [bedrooms], [orientation]`  
- Lease: `id, unit_id, status, start/end, rent_monthly, deposit, tenant_hash`  
- Permit: `scope='building'`, `kind='occupancy'`, `status`, `issued_on/completed_on`  
- Title: `deed_no`, `encumbrance_json.lien_status`, `effective_on`  
- Meter: electricity readings (daily is fine): `(meter_id, ts, value)`

**Tier‑1 (nice to have early):**
- Admin geography (city/district/neighborhood codes), POI distances, hazards  
- Sales/rent comps, price indices, off‑plan supply nearby  
- Floor‑plan metrics, façade/MEP types, retrofit timestamps  
- Opex buckets, maintenance tickets, occupancy history

> **Saudi context** (optional): public aggregates exist (REGA indicators, GASTAT real estate price index, Wafi projects), while micro‑level deeds/permits/leases are portal‑gated (Najiz, Balady, Ejar) and available with party consent.

---

## Design choices & best practices

- **Separation of concerns**:  
  `models.py` (domain) ← `db.py` (I/O) ← `features.py` (pure functions) ← `cli.py` (orchestration).
- **Typed dataclasses** for clarity and testing.  
- **PostGIS** for geometry; pass WKT to Python to keep the app light.  
- **Trivial vs Inference**: ship value fast with algebraic metrics; add models in the TODOs.  
- **Auditability**: every metric maps to a field/row with a clear lineage.

---

## Extending: where to put your models

- Add modules: `proptech/inference_avm.py`, `inference_credit.py`, `inference_mbs.py`.  
- Keep interfaces **pure functions**: `(dataclasses, config) -> outputs`.  
- Wire into `cli.py` via flags or subcommands (`--with-avm`, `--with-pd-lgd`).

---

## Testing (recommended)

- Unit‑test **features** without a DB (construct dataclasses directly).  
- For DB tests, use a temporary schema or transaction rollbacks.  
- Suggested stack: `pytest`, `pytest-cov`, `mypy`/`pyright`.

Example:
```bash
pip install pytest
pytest -q
```

---

## Security, privacy & compliance

- Use **pseudonymous IDs** (`tenant_hash`, `owner_hash`) and segregate any PII.  
- Pull portal data only with **user consent**; store **provenance** and timestamps.  
- For finance workflows (origination/securitization), emit an **immutable evidence pack** (JSON + PDFs where available).

---

## Roadmap (suggested next steps)

- Add **Pandas** bulk loaders for notebooks.  
- Implement a minimal **AVM** (nearest‑neighbor comps with time/quality adjustments).  
- Add an **open‑banking** adapter for affordability (if applicable).  
- Build **RMBS** export templates and eligibility checks.  
- Create **Grafana/Metabase** dashboards for core KPIs (occupancy, energy intensity, NOI).  
- Integrate **Alembic** for DB migrations.

---

## Contact / Support


