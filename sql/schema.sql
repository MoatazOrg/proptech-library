-- Tables (match your dataclasses)
CREATE TABLE IF NOT EXISTS parcel(
  id UUID PRIMARY KEY,
  muni_id TEXT,
  zoning TEXT,
  geom GEOMETRY(POLYGON, 4326)
);
CREATE INDEX IF NOT EXISTS parcel_geom_gix ON parcel USING GIST(geom);

CREATE TABLE IF NOT EXISTS building(
  id UUID PRIMARY KEY,
  parcel_id UUID REFERENCES parcel(id),
  year_built SMALLINT,
  structure TEXT,
  floors SMALLINT,
  bua_m2 NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS unit(
  id UUID PRIMARY KEY,
  building_id UUID REFERENCES building(id),
  use_type TEXT,
  nla_m2 NUMERIC(12,2),
  floor_no SMALLINT,
  bedrooms SMALLINT,
  orientation TEXT
);

CREATE TABLE IF NOT EXISTS lease(
  id UUID PRIMARY KEY,
  unit_id UUID REFERENCES unit(id),
  tenant_hash TEXT,
  start_date DATE,
  end_date DATE,
  rent_monthly NUMERIC(12,2),
  deposit NUMERIC(12,2),
  status TEXT
);

CREATE TABLE IF NOT EXISTS meter(
  id UUID PRIMARY KEY,
  scope TEXT CHECK (scope IN ('building','unit')),
  scope_id UUID,
  type TEXT,
  provider_acct TEXT
);

CREATE TABLE IF NOT EXISTS meter_reading(
  meter_id UUID REFERENCES meter(id),
  ts TIMESTAMPTZ,
  value NUMERIC(14,4),
  PRIMARY KEY (meter_id, ts)
);

CREATE TABLE IF NOT EXISTS permit(
  id UUID PRIMARY KEY,
  scope TEXT CHECK (scope IN ('parcel','building','unit')),
  scope_id UUID,
  kind TEXT,
  status TEXT,
  issued_on DATE,
  completed_on DATE,
  permit_no TEXT
);

CREATE TABLE IF NOT EXISTS title_record(
  id UUID PRIMARY KEY,
  scope TEXT CHECK (scope IN ('parcel','unit')),
  scope_id UUID,
  owner_hash TEXT,
  deed_no TEXT,
  encumbrance_json JSONB,
  effective_on DATE
);

-- View to pull a “unit chain”
CREATE OR REPLACE VIEW v_unit_core AS
SELECT
  u.id            AS unit_id,
  u.building_id,
  b.parcel_id,
  u.use_type      AS unit_use_type,
  u.nla_m2,
  u.floor_no,
  u.bedrooms,
  u.orientation,
  b.year_built,
  b.structure,
  b.floors,
  b.bua_m2,
  p.muni_id,
  p.zoning,
  ST_AsText(p.geom) AS parcel_geom_wkt
FROM unit u
JOIN building b ON b.id = u.building_id
JOIN parcel   p ON p.id = b.parcel_id;
