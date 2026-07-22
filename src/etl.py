"""Transforming raw sources into clean frames and load them into Postgres"""
import logging
import numpy as np
import os

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("etl")

USDA_PATH = "data/raw/food_access_atlas_2019.xlsx"
ACS_PATH = "data/raw/acs_worcester_2019.csv"
TIGER_PATH = "zip://data/raw/tl_2019_25_tract.zip"


def transform_usda() -> pd.DataFrame:
    xl = pd.ExcelFile(USDA_PATH)
    sheet = [s for s in xl.sheet_names if "Atlas" in s][0]
    df = pd.read_excel(USDA_PATH, sheet_name=sheet, dtype={"CensusTract": str})
    df = df[df["State"].str.contains("Massachusetts", na=False)]
    df = df[df["County"].str.contains("Worcester", na=False)].copy()
    log.info("USDA rows after filter: %d", len(df))

    out = pd.DataFrame({
        "geoid": df["CensusTract"].str.zfill(11),
        "access_share_1mi": pd.to_numeric(df["lapop1share"], errors="coerce"),
        "access_share_10mi": pd.to_numeric(df["lapop10share"], errors="coerce"),
        "urban": df["Urban"].astype(float).fillna(0).astype(int).astype(bool),
        "low_income_flag": df["LowIncomeTracts"].astype(float).fillna(0).astype(int).astype(bool),
        "lila_flag": df["LILATracts_1And10"].astype(float).fillna(0).astype(int).astype(bool),
    })

    # If shares came through as proportions (max <= 1), convert to percent
    for col in ("access_share_1mi", "access_share_10mi"):
        if out[col].max() is not pd.NA and out[col].max() <= 1.5:
            out[col] = out[col] * 100
            log.info("%s looked like a proportion; converted to percent", col)

    # SNAP share from USDA counts (kept here so demographics has one row per tract)
    ohu = pd.to_numeric(df["OHU2010"], errors="coerce")
    snap = pd.to_numeric(df["TractSNAP"], errors="coerce")
    out["pct_snap_household"] = (snap / ohu.replace(0, np.nan) * 100).round(2)
    return out


def transform_acs() -> pd.DataFrame:
    df = pd.read_csv(ACS_PATH, dtype={"geoid": str})
    out = pd.DataFrame({
        "geoid": df["geoid"].str.zfill(11),
        "median_income": df["median_income"],
        "poverty_rate": (df["pov_below"] / df["pov_universe"].replace(0, np.nan) * 100).round(2),
        "pct_no_vehicle": (df["hh_no_vehicle"] / df["hh_total"].replace(0, np.nan) * 100).round(2),
        "total_pop": df["total_pop"].astype("Int64"),
        "tract_name": df["NAME"],
    })
    log.info("ACS rows: %d", len(out))
    return out


def transform_tiger() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(TIGER_PATH)
    gdf = gdf[gdf["COUNTYFP"] == "027"].copy()
    gdf = gdf.to_crs(epsg=4326)
    # Force MultiPolygon so every row matches the geom column type in Postgres
    from shapely.geometry import MultiPolygon, Polygon
    gdf["geometry"] = gdf["geometry"].apply(
        lambda g: MultiPolygon([g]) if isinstance(g, Polygon) else g
    )
    out = gpd.GeoDataFrame({
        "geoid": gdf["GEOID"].astype(str).str.zfill(11),
        "state": "MA",
        "county": "Worcester",
    }, geometry=gdf["geometry"], crs="EPSG:4326")
    out = out.rename_geometry("geom")
    log.info("TIGER rows: %d", len(out))
    return out


def load(engine) -> None:
    usda = transform_usda()
    acs = transform_acs()
    tiger = transform_tiger()

    # Keep only tracts present everywhere (documented, deliberate inner-join scope)
    common = set(usda["geoid"]) & set(acs["geoid"]) & set(tiger["geoid"])
    log.info("Common GEOIDs across all sources: %d", len(common))

    tracts = tiger[tiger["geoid"].isin(common)].merge(
        acs[["geoid", "total_pop", "tract_name"]], on="geoid"
    )
    demographics = acs[acs["geoid"].isin(common)][
        ["geoid", "median_income", "poverty_rate", "pct_no_vehicle"]
    ].merge(usda[["geoid", "pct_snap_household"]], on="geoid")
    food_access = usda[usda["geoid"].isin(common)][
        ["geoid", "access_share_1mi", "access_share_10mi",
         "urban", "low_income_flag", "lila_flag"]
    ]

    with engine.begin() as conn:  # one transaction: all-or-nothing reload
        conn.execute(text(
            "TRUNCATE food_access, demographics, tracts"
        ))
    tracts.to_postgis("tracts", engine, if_exists="append", index=False)
    demographics.to_sql("demographics", engine, if_exists="append", index=False)
    food_access.to_sql("food_access", engine, if_exists="append", index=False)
    log.info("Loaded: tracts=%d demographics=%d food_access=%d",
             len(tracts), len(demographics), len(food_access))


if __name__ == "__main__":
    engine = create_engine(os.environ["DATABASE_URL"])
    load(engine)
    log.info("ETL complete.")