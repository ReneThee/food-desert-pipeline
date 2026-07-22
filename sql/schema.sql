
CREATE EXTENSION IF NOT EXISTS postgis;

DROP VIEW IF EXISTS food_desert_tracts;
DROP VIEW IF EXISTS food_desert_score;
DROP TABLE IF EXISTS food_access;
DROP TABLE IF EXISTS demographics;
DROP TABLE IF EXISTS tracts;

CREATE TABLE tracts (
    geoid       CHAR(11) PRIMARY KEY,
    state       TEXT NOT NULL,
    county      TEXT NOT NULL,
    tract_name  TEXT,
    total_pop   INTEGER,
    geom        GEOMETRY(MULTIPOLYGON, 4326)
);

CREATE TABLE demographics (
    geoid              CHAR(11) PRIMARY KEY REFERENCES tracts(geoid),
    median_income      NUMERIC,
    poverty_rate       NUMERIC,   -- percent 0-100
    pct_no_vehicle     NUMERIC,   -- percent of households, 0-100
    pct_snap_household NUMERIC    -- percent of occupied housing units, 0-100
);

CREATE TABLE food_access (
    geoid             CHAR(11) PRIMARY KEY REFERENCES tracts(geoid),
    access_share_1mi  NUMERIC,   -- % of pop >1 mile from supermarket (urban std)
    access_share_10mi NUMERIC,   -- % of pop >10 miles (rural std)
    urban             BOOLEAN,
    low_income_flag   BOOLEAN,   -- USDA benchmark only
    lila_flag         BOOLEAN    -- USDA LILA 1&10 benchmark only, NOT a score input
);