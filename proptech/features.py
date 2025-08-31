# ============================================================
# 15 output families — Trivial formulas & TODO(Inference)
# Append below your existing dataclasses & helpers
# ============================================================

from datetime import date
from typing import Iterable, Tuple, Dict, List, Optional
import math
import statistics as stats

# ------------------------------------------------------------
# 1) Valuation & investment metrics
# ------------------------------------------------------------

def noi(rent_monthly_sum: float, other_income_monthly: float, opex_monthly: float) -> float:
    """NOI (annualized) = (Rent + Other income - Opex) * 12"""
    return (rent_monthly_sum + other_income_monthly - opex_monthly) * 12.0

def cap_rate(noi_annual: float, value: float) -> float:
    """Cap rate = NOI / Value"""
    return 0.0 if value <= 0 else noi_annual / value

def value_from_cap(noi_annual: float, market_cap_rate: float) -> float:
    """Value = NOI / CapRate"""
    return float('inf') if market_cap_rate <= 0 else noi_annual / market_cap_rate

def dscr(noi_annual: float, annual_debt_service: float) -> float:
    """DSCR = NOI / Debt service"""
    return 0.0 if annual_debt_service <= 0 else noi_annual / annual_debt_service

def equity_multiple(total_distributions: float, total_equity_invested: float) -> float:
    """Equity multiple = Total distributions / Equity invested"""
    return 0.0 if total_equity_invested <= 0 else total_distributions / total_equity_invested

def yield_on_cost(stabilized_noi_annual: float, total_project_cost: float) -> float:
    """Yield-on-cost = Stabilized NOI / Total cost"""
    return 0.0 if total_project_cost <= 0 else stabilized_noi_annual / total_project_cost

# TODO Inference: AVM fair value from comps (hedonic/kNN), IRR/NPV w/ stochastic vacancy,
# market-implied cap rate, condition/obsolescence scoring.


# ------------------------------------------------------------
# 2) Lending & borrower affordability
# ------------------------------------------------------------

def ltv(current_loan_balance: float, property_value: float) -> float:
    """LTV = Loan balance / Property value"""
    return 0.0 if property_value <= 0 else current_loan_balance / property_value

def cltv(total_liens_balance: float, property_value: float) -> float:
    """CLTV = Sum of liens / Property value"""
    return 0.0 if property_value <= 0 else total_liens_balance / property_value

def dti(monthly_debt_obligations: float, monthly_gross_income: float) -> float:
    """DTI = Monthly debts / Monthly income"""
    return 0.0 if monthly_gross_income <= 0 else monthly_debt_obligations / monthly_gross_income

def residual_income(monthly_income: float, monthly_expenses_ex_debt: float, monthly_debt: float) -> float:
    """Residual income = Income - (non-debt expenses + debt)"""
    return monthly_income - (monthly_expenses_ex_debt + monthly_debt)

# TODO Inference: PD/LGD/EAD modeling, income stability via open-banking time series,
# HPI-adjusted forward LTV projections.


# ------------------------------------------------------------
# 3) Capital-markets & securitization
# ------------------------------------------------------------

def tape_qc_flags(
    valuation_date: Optional[date],
    permit_completed_on: Optional[date],
    title_clean_flag: bool
) -> Dict[str, bool]:
    """Simple eligibility/QC flags"""
    return {
        "valuation_missing": valuation_date is None,
        "permit_stale": (permit_completed_on is None) or ((date.today() - permit_completed_on).days > 3650),
        "title_not_clean": not title_clean_flag,
    }

def weighted_average_life(schedule: Iterable[Tuple[date, float]]) -> float:
    """
    WAL ≈ sum( t_years * principal_i ) / sum(principal_i)
    schedule: iterable of (date_i, principal_payment_i) where principal_payment_i >= 0
    """
    items = list(schedule)
    if not items:
        return 0.0
    total_prin = sum(p for _, p in items)
    if total_prin <= 0:
        return 0.0
    t0 = min(d for d, _ in items)
    def years_between(d: date) -> float:
        return (d - t0).days / 365.25
    return sum(years_between(d) * p for d, p in items) / total_prin

# TODO Inference: CPR/CDR/severity projections, tranche waterfall simulations,
# pool correlation/dispersion analytics, trigger breach forecasting.


# ------------------------------------------------------------
# 4) Leasing & revenue management
# ------------------------------------------------------------

def rent_roll_total(active_leases: Iterable[Lease]) -> float:
    """Sum of monthly rent for active leases"""
    return sum(l.rent_monthly for l in active_leases if l.status == "active")

def occupancy_rate(units: Iterable[Unit], leases: Iterable[Lease]) -> float:
    """Occupancy = active leased units / total units (unit considered occupied if any active lease)"""
    unit_ids = {u.id for u in units}
    occupied = {l.unit_id for l in leases if l.status == "active"}
    denom = len(unit_ids)
    return 0.0 if denom == 0 else len(unit_ids & occupied) / denom

def avg_time_to_lease(days_vacant_list: Iterable[int]) -> float:
    """Average days-to-lease from historical records"""
    lst = list(days_vacant_list)
    return 0.0 if not lst else sum(lst) / len(lst)

# TODO Inference: market rent recommendation engine (comp selection/weighting),
# renewal/churn propensity, concession optimization, price elasticity by attributes.


# ------------------------------------------------------------
# 5) Operations, maintenance & CapEx
# ------------------------------------------------------------

def kwh_per_m2_day_from_series(unit_obj: Unit, readings_daily_kwh: Iterable[float]) -> float:
    """Average energy intensity given daily kWh readings"""
    vals = list(readings_daily_kwh)
    if unit_obj.nla_m2 <= 0 or not vals:
        return 0.0
    return (sum(vals) / len(vals)) / unit_obj.nla_m2

def mttr(total_repair_time_hours: float, tickets_closed: int) -> float:
    """Mean Time To Repair = total hours repairing / tickets closed"""
    return 0.0 if tickets_closed <= 0 else total_repair_time_hours / tickets_closed

def opex_per_unit(total_opex_monthly: float, unit_count: int) -> float:
    """Monthly Opex per unit"""
    return 0.0 if unit_count <= 0 else total_opex_monthly / unit_count

# TODO Inference: predictive failure risk (HVAC), weather/usage-normalized Opex benchmarks,
# optimal retrofit timing under failure probabilities.


# ------------------------------------------------------------
# 6) Compliance, permits, legal certainty
# ------------------------------------------------------------

def days_since_last_occupancy(perm: Optional[Permit]) -> Optional[int]:
    """Days since occupancy completion; None if not completed"""
    if perm is None or perm.completed_on is None:
        return None
    return (date.today() - perm.completed_on).days

def title_clean_flag_from_record(t: Optional[TitleRecord]) -> bool:
    """True if lien_status in {free, released}"""
    if t is None:
        return False
    return t.encumbrance.get("lien_status", "").lower() in {"free", "released"}

def zoning_mismatch(actual_use: str, zoning_code: str, allowed_map: Dict[str, List[str]]) -> bool:
    """True if actual use not allowed by zoning (simple lookup)"""
    allowed = allowed_map.get(zoning_code, [])
    return actual_use not in allowed

# TODO Inference: comprehensive compliance risk score, likelihood of permit delays,
# detection of unpermitted alterations from patterns.


# ------------------------------------------------------------
# 7) ESG, energy & resilience
# ------------------------------------------------------------

def carbon_intensity_kgco2e_per_m2_year(kwh_per_m2_year: float, grid_factor_kgco2e_per_kwh: float) -> float:
    """Scope-2 proxy: kWh/m²/yr × grid emission factor"""
    return kwh_per_m2_year * grid_factor_kgco2e_per_kwh

def water_intensity_m3_per_m2_year(m3_per_year: float, nla_m2: float) -> float:
    return 0.0 if nla_m2 <= 0 else m3_per_year / nla_m2

def simple_hazard_distance_score(distance_m: float, threshold_m: float = 500.0) -> float:
    """1.0 if far, 0.0 if at hazard; linear between 0..threshold"""
    if distance_m >= threshold_m:
        return 1.0
    return max(0.0, distance_m / threshold_m)

# TODO Inference: retrofit savings estimation (baselines), multi-hazard resilience index,
# IAQ/comfort scoring from sensor patterns.


# ------------------------------------------------------------
# 8) Market intelligence & strategy
# ------------------------------------------------------------

def median(values: Iterable[float]) -> float:
    vals = [v for v in values if v is not None]
    return 0.0 if not vals else float(stats.median(vals))

def neighborhood_median_rent(rents: Iterable[float]) -> float:
    return median(rents)

def supply_count(offplan_projects_within_radius: Iterable[object]) -> int:
    """Count of off-plan projects nearby (pass iterable of matched items)"""
    return sum(1 for _ in offplan_projects_within_radius)

def turnover_rate(leases_ended: int, total_units: int) -> float:
    return 0.0 if total_units <= 0 else leases_ended / total_units

# TODO Inference: time/quality-adjusted comp indices, amenity travel-time scoring,
# gentrification/affordability trend detection.


# ------------------------------------------------------------
# 9) Development & site selection
# ------------------------------------------------------------

def far(gfa_m2: float, lot_area_m2: float) -> float:
    """FAR = Gross floor area / Lot area"""
    return 0.0 if lot_area_m2 <= 0 else gfa_m2 / lot_area_m2

def coverage_ratio(footprint_m2: float, lot_area_m2: float) -> float:
    """Site coverage = Building footprint / Lot area"""
    return 0.0 if lot_area_m2 <= 0 else footprint_m2 / lot_area_m2

def parking_ratio(spaces: int, units_count: int) -> float:
    """Parking spaces per unit"""
    return 0.0 if units_count <= 0 else spaces / units_count

# TODO Inference: highest & best use recommendation engine, absorption & price–mix optimizer,
# critical-path delay risk modeling.


# ------------------------------------------------------------
# 10) Insurance & risk transfer
# ------------------------------------------------------------

def sum_insured_from_replacement_cost(bua_m2: float, cost_rate_sar_per_m2: float) -> float:
    """Replacement cost estimate"""
    return bua_m2 * cost_rate_sar_per_m2

def deductible_effect_expected_cost(expected_annual_claim_sar: float, deductible_sar: float, claim_count_per_year: float) -> float:
    """
    Toy: reduces expected cost by min(deductible, expected per-claim) * expected claim count
    """
    if claim_count_per_year <= 0:
        return expected_annual_claim_sar
    expected_per_claim = expected_annual_claim_sar / claim_count_per_year
    reduction = min(deductible_sar, expected_per_claim) * claim_count_per_year
    return max(0.0, expected_annual_claim_sar - reduction)

# TODO Inference: peril loss curves (flood/fire/seismic), premium optimization,
# business-interruption exposure modeling from NOI.


# ------------------------------------------------------------
# 11) Fraud, anomaly & governance
# ------------------------------------------------------------

def area_sanity_flag(nla_m2: float, bua_m2: float, tolerance: float = 1.0) -> bool:
    """Flag if NLA > BUA (beyond tolerance m²)"""
    return nla_m2 > (bua_m2 + tolerance)

def occupancy_vs_usage_flag(is_occupied: bool, avg_kwh_per_day: float, min_kwh_threshold: float = 1.0) -> bool:
    """Flag if claimed occupied but usage is near-zero"""
    return is_occupied and (avg_kwh_per_day < min_kwh_threshold)

# TODO Inference: synthetic identity detection, title/permit inconsistency scoring,
# data lineage quality scoring with provenance weights.


# ------------------------------------------------------------
# 12) Tenant/occupant analytics
# ------------------------------------------------------------

def avg_satisfaction(scores_1_to_5: Iterable[float]) -> float:
    vals = [s for s in scores_1_to_5 if s is not None]
    return 0.0 if not vals else sum(vals) / len(vals)

def amenity_utilization(used_slots: int, total_slots: int) -> float:
    return 0.0 if total_slots <= 0 else used_slots / total_slots

def cohort_churn_rate(ended_leases_in_cohort: int, cohort_size: int) -> float:
    return 0.0 if cohort_size <= 0 else ended_leases_in_cohort / cohort_size

# TODO Inference: churn driver attribution, optimal amenity pricing/scheduling,
# sentiment modeling from free-text tickets/notes.


# ------------------------------------------------------------
# 13) Portfolio construction & hedging
# ------------------------------------------------------------

def exposure_by_bucket(values_by_bucket: Iterable[Tuple[str, float]]) -> Dict[str, float]:
    """Aggregate value by bucket (e.g., region/segment)"""
    agg: Dict[str, float] = {}
    for bucket, v in values_by_bucket:
        agg[bucket] = agg.get(bucket, 0.0) + v
    return agg

def weighted_yield(weights_and_yields: Iterable[Tuple[float, float]]) -> float:
    """Sum(w_i * y_i) where weights sum to 1 (not enforced here)"""
    pairs = list(weights_and_yields)
    if not pairs:
        return 0.0
    return sum(w * y for w, y in pairs)

def simple_risk_parity_weights(variances: Dict[str, float]) -> Dict[str, float]:
    """Inverse-variance weighting normalized to 1"""
    inv = {k: (0.0 if v <= 0 else 1.0 / v) for k, v in variances.items()}
    total = sum(inv.values())
    return {k: (0.0 if total == 0 else inv[k] / total) for k in inv}

# TODO Inference: efficient frontier (mean–variance/factors), factor exposure estimation,
# hedge selection/sizing via scenario optimization.


# ------------------------------------------------------------
# 14) Islamic finance (Murabaha / Ijara / Diminishing Musharaka)
# ------------------------------------------------------------

def murabaha_equal_installments_schedule(cost_price: float, profit_markup: float, months: int) -> List[float]:
    """
    Simple Murabaha: total price = cost * (1 + markup); equal monthly installments = total / months
    (No interest mechanics; markup is pre-agreed profit)
    """
    total_price = cost_price * (1.0 + profit_markup)
    if months <= 0:
        return [total_price]
    installment = total_price / months
    return [installment for _ in range(months)]

def ijara_monthly_rent(asset_cost: float, annual_profit_rate: float, months: int) -> float:
    """
    Toy Ijara rent per month: asset_cost * annual_rate / 12
    (In practice, structure may differ; this is a trivial proxy.)
    """
    return (asset_cost * annual_profit_rate) / 12.0

# TODO Inference: Sharia compliance evidence scoring (possession/risk), profit-rate sensitivities,
# residual value risk at end-of-term under alternative cost bases.


# ------------------------------------------------------------
# 15) Standard reports & exports (structured dicts)
# ------------------------------------------------------------

def los_package_dict(
    u: Unit, b: Building, p: Parcel,
    latest_title: Optional[TitleRecord],
    latest_permit: Optional[Permit],
    avm_value: Optional[float],
    valuation_date: Optional[date]
) -> Dict[str, object]:
    """Minimal LOS/underwriting export as a dict (serialize to JSON as needed)"""
    return {
        "parcel": {"id": str(p.id), "muni_id": p.muni_id, "zoning": p.zoning},
        "building": {"id": str(b.id), "year_built": b.year_built, "floors": b.floors, "bua_m2": b.bua_m2},
        "unit": {"id": str(u.id), "use_type": u.use_type, "nla_m2": u.nla_m2, "floor_no": u.floor_no},
        "title": {
            "present": latest_title is not None,
            "deed_no": (latest_title.deed_no if latest_title else None),
            "clean": title_clean_flag_from_record(latest_title),
        },
        "permit_occupancy": {
            "present": (latest_permit is not None and latest_permit.kind == "occupancy"),
            "completed_on": (latest_permit.completed_on if latest_permit else None),
        },
        "valuation": {"avm_value": avm_value, "valuation_date": valuation_date},
        "generated_on": date.today().isoformat()
    }

# TODO Inference: data-minimization/redaction by recipient role, anomaly-aware highlighting,
# confidence-weighted disclosures per field.
