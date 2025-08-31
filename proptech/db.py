import os
from uuid import UUID
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Tuple
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

from .models import (
    Parcel, Building, Unit, Lease, Meter, MeterReading, Permit, TitleRecord
)

load_dotenv()  # load .env if present

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/propdb")
engine = create_engine(DB_URL, future=True)

# --------- mappers ---------

def _map_unit_chain(row) -> Tuple[Unit, Building, Parcel]:
    u = Unit(
        id=UUID(row["unit_id"]),
        building_id=UUID(row["building_id"]),
        use_type=row["unit_use_type"],
        nla_m2=float(row["nla_m2"] or 0.0),
        floor_no=int(row["floor_no"] or 0),
        bedrooms=(int(row["bedrooms"]) if row["bedrooms"] is not None else None),
        orientation=row["orientation"],
    )
    b = Building(
        id=UUID(row["building_id"]),
        parcel_id=UUID(row["parcel_id"]),
        year_built=int(row["year_built"] or 0),
        structure=row["structure"],
        floors=int(row["floors"] or 0),
        bua_m2=float(row["bua_m2"] or 0.0),
    )
    p = Parcel(
        id=UUID(row["parcel_id"]),
        muni_id=row["muni_id"],
        zoning=row["zoning"],
        geom_wkt=row["parcel_geom_wkt"],
    )
    return u, b, p

def _map_lease(row) -> Lease:
    return Lease(
        id=UUID(row["id"]),
        unit_id=UUID(row["unit_id"]),
        tenant_hash=row["tenant_hash"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        rent_monthly=float(row["rent_monthly"] or 0.0),
        deposit=float(row["deposit"] or 0.0),
        status=row["status"],
    )

def _map_permit(row) -> Permit:
    return Permit(
        id=UUID(row["id"]),
        scope=row["scope"],
        scope_id=UUID(row["scope_id"]),
        kind=row["kind"],
        status=row["status"],
        issued_on=row["issued_on"],
        completed_on=row["completed_on"],
        permit_no=row["permit_no"],
    )

def _map_title(row) -> TitleRecord:
    enc = row["encumbrance_json"]
    if isinstance(enc, str):
        try:
            import json; enc = json.loads(enc)
        except Exception:
            enc = {}
    return TitleRecord(
        id=UUID(row["id"]),
        scope=row["scope"],
        scope_id=UUID(row["scope_id"]),
        owner_hash=row["owner_hash"],
        deed_no=row["deed_no"],
        encumbrance=enc or {},
        effective_on=row["effective_on"],
    )

def _map_meter(row) -> Meter:
    return Meter(
        id=UUID(row["id"]),
        scope=row["scope"],
        scope_id=UUID(row["scope_id"]),
        type=row["type"],
        provider_acct=row["provider_acct"],
    )

def _map_reading(row) -> MeterReading:
    return MeterReading(
        meter_id=UUID(row["meter_id"]),
        ts=row["ts"],
        value=float(row["value"]),
    )

# --------- fetchers ---------

def fetch_unit_core(unit_id: UUID) -> Tuple[Unit, Building, Parcel]:
    sql = text("SELECT * FROM v_unit_core WHERE unit_id = :uid")
    with engine.begin() as conn:
        row = conn.execute(sql, {"uid": str(unit_id)}).mappings().first()
    if not row:
        raise ValueError(f"Unit {unit_id} not found")
    return _map_unit_chain(row)

def fetch_active_leases(unit_id: UUID) -> List[Lease]:
    sql = text("""
        SELECT * FROM lease
        WHERE unit_id = :uid AND status = 'active'
        ORDER BY start_date DESC
    """)
    with engine.begin() as conn:
        rows = conn.execute(sql, {"uid": str(unit_id)}).mappings().all()
    return [_map_lease(r) for r in rows]

def fetch_latest_permit_for_building(building_id: UUID) -> Optional[Permit]:
    sql = text("""
        SELECT * FROM permit
        WHERE scope='building' AND scope_id=:bid
          AND kind IN ('occupancy','completion')
        ORDER BY completed_on DESC NULLS LAST, issued_on DESC NULLS LAST
        LIMIT 1
    """)
    with engine.begin() as conn:
        row = conn.execute(sql, {"bid": str(building_id)}).mappings().first()
    return _map_permit(row) if row else None

def fetch_latest_title(unit_id: UUID, parcel_id: UUID) -> Optional[TitleRecord]:
    sql_unit = text("""
        SELECT * FROM title_record
        WHERE scope='unit' AND scope_id=:uid
        ORDER BY effective_on DESC LIMIT 1
    """)
    sql_parcel = text("""
        SELECT * FROM title_record
        WHERE scope='parcel' AND scope_id=:pid
        ORDER BY effective_on DESC LIMIT 1
    """)
    with engine.begin() as conn:
        row = conn.execute(sql_unit, {"uid": str(unit_id)}).mappings().first()
        if row: return _map_title(row)
        row = conn.execute(sql_parcel, {"pid": str(parcel_id)}).mappings().first()
        return _map_title(row) if row else None

def fetch_unit_meters(unit_id: UUID) -> List[Meter]:
    sql = text("SELECT * FROM meter WHERE scope='unit' AND scope_id=:uid")
    with engine.begin() as conn:
        rows = conn.execute(sql, {"uid": str(unit_id)}).mappings().all()
    return [_map_meter(r) for r in rows]

def fetch_readings(meter_id: UUID, days_back: int = 30) -> List[MeterReading]:
    ts_from = datetime.utcnow() - timedelta(days=days_back)
    sql = text("""
        SELECT * FROM meter_reading
        WHERE meter_id=:mid AND ts >= :ts_from
        ORDER BY ts
    """)
    with engine.begin() as conn:
        rows = conn.execute(sql, {"mid": str(meter_id), "ts_from": ts_from}).mappings().all()
    return [_map_reading(r) for r in rows]
