from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Literal, Dict
from datetime import date, datetime
from uuid import UUID

# --------- Core dataclasses ---------

@dataclass(frozen=True)
class Parcel:
    id: UUID
    muni_id: str
    zoning: str
    geom_wkt: str  # polygon in WKT (EPSG:4326)

@dataclass(frozen=True)
class Building:
    id: UUID
    parcel_id: UUID
    year_built: int
    structure: str
    floors: int
    bua_m2: float

@dataclass(frozen=True)
class Unit:
    id: UUID
    building_id: UUID
    use_type: str
    nla_m2: float
    floor_no: int
    bedrooms: Optional[int] = None
    orientation: Optional[str] = None

@dataclass(frozen=True)
class Lease:
    id: UUID
    unit_id: UUID
    tenant_hash: str
    start_date: date
    end_date: date
    rent_monthly: float
    deposit: float
    status: Literal["planned", "active", "expired", "defaulted"]

@dataclass(frozen=True)
class Meter:
    id: UUID
    scope: Literal["building", "unit"]
    scope_id: UUID
    type: str
    provider_acct: Optional[str] = None

@dataclass(frozen=True)
class MeterReading:
    meter_id: UUID
    ts: datetime
    value: float

@dataclass(frozen=True)
class Permit:
    id: UUID
    scope: Literal["parcel","building","unit"]
    scope_id: UUID
    kind: str
    status: Literal["issued","completed","revoked","expired"]
    issued_on: date
    completed_on: Optional[date]
    permit_no: str

@dataclass(frozen=True)
class TitleRecord:
    id: UUID
    scope: Literal["parcel","unit"]
    scope_id: UUID
    owner_hash: str
    deed_no: str
    encumbrance: Dict[str, str]
    effective_on: date

# --------- Low-level helpers (used by CLI/examples) ---------

def building_age_years(b: Building, asof: date | None = None) -> int:
    asof = asof or date.today()
    return max(0, asof.year - int(b.year_built))

def title_clean_flag_from_record(t: TitleRecord | None) -> bool:
    if t is None:
        return False
    return t.encumbrance.get("lien_status", "").lower() in {"free", "released"}
