import argparse, json
from uuid import UUID
from datetime import date
from .db import (
    fetch_unit_core, fetch_active_leases, fetch_latest_permit_for_building,
    fetch_latest_title, fetch_unit_meters, fetch_readings
)
from .models import building_age_years, TitleRecord
from .features import (
    rent_roll_total, noi, occupancy_rate, days_since_last_occupancy,
    title_clean_flag_from_record, kwh_per_m2_day_from_series,
    ltv, cap_rate, value_from_cap
)

def main():
    ap = argparse.ArgumentParser(description="PropTech demo CLI")
    ap.add_argument("--unit-id", required=True, type=UUID, help="Unit UUID")
    ap.add_argument("--days-back", type=int, default=7)
    ap.add_argument("--assumed-cap-rate", type=float, default=0.06)
    ap.add_argument("--loan-balance", type=float, default=0.0)
    args = ap.parse_args()

    # Load chain
    u, b, p = fetch_unit_core(args.unit_id)
    leases = fetch_active_leases(u.id)
    permit = fetch_latest_permit_for_building(b.id)
    title = fetch_latest_title(u.id, p.id)
    meters = fetch_unit_meters(u.id)
    elec = next((m for m in meters if m.type == "electricity"), None)
    readings = fetch_readings(elec.id, days_back=args.days_back) if elec else []

    # Trivial metrics
    monthly_rent = rent_roll_total(leases)
    annual_noi = noi(monthly_rent, other_income_monthly=0.0, opex_monthly=0.0)
    assumed_value = value_from_cap(annual_noi, args.assumed_cap_rate)
    current_ltv = ltv(args.loan_balance, assumed_value) if args.loan_balance > 0 else None
    occ_rate = occupancy_rate([u], leases)
    days_since_occ = days_since_last_occupancy(permit)
    title_ok = title_clean_flag_from_record(title)

    # Energy intensity (kWh/m²/day) from readings
    by_day = {}
    for r in readings:
        d = r.ts.date()
        by_day[d] = by_day.get(d, 0.0) + r.value
    intensity = kwh_per_m2_day_from_series(u, list(by_day.values())) if by_day else 0.0

    out = {
        "parcel": {"zoning": p.zoning, "muni_id": p.muni_id},
        "building": {"age_years": building_age_years(b), "floors": b.floors, "bua_m2": b.bua_m2},
        "unit": {"use_type": u.use_type, "nla_m2": u.nla_m2, "floor_no": u.floor_no},
        "leases": {"active_count": len(leases), "rent_monthly_total": monthly_rent},
        "valuation": {
            "assumed_cap_rate": args.assumed_cap_rate,
            "noi_annual": annual_noi,
            "implied_value": assumed_value,
            "ltv_from_input_balance": current_ltv,
        },
        "compliance": {"days_since_occupancy": days_since_occ, "title_clean": title_ok},
        "energy": {"kwh_per_m2_day": intensity, "window_days": args.days_back},
        # TODO Inference hooks: AVM, PD/LGD, CPR/CDR, rent recommendations, etc.
        "_meta": {"generated_on": date.today().isoformat()}
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
