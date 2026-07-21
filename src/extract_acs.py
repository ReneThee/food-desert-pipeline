"""Pulling ACS 2019 5-year tract data for Worcester County via the Census API."""
import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv() 
API_KEY = os.environ["CENSUS_API_KEY"]  

YEAR = 2019          # last vintage on 2010 tract boundaries — see Part 0
STATE_FIPS = "25"    # Massachusetts
COUNTY_FIPS = "027"  # Worcester County

# Census variable code -> column name
VARS = {
    "B01003_001E": "total_pop",        # total population
    "B19013_001E": "median_income",    # median household income ($)
    "B17001_001E": "pov_universe",     # population poverty status is known for
    "B17001_002E": "pov_below",        # population below poverty line
    "B08201_001E": "hh_total",         # total households
    "B08201_002E": "hh_no_vehicle",    # households with zero vehicles
}

def fetch_acs() -> pd.DataFrame:
    url = f"https://api.census.gov/data/{YEAR}/acs/acs5"
    params = {
        "get": "NAME," + ",".join(VARS),
        "for": "tract:*",
        "in": f"state:{STATE_FIPS} county:{COUNTY_FIPS}",
        "key": API_KEY,
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    print("Status:", resp.status_code)
    print("First 300 chars of response:", resp.text[:300])  # crash loudly on a bad key / bad request
    rows = resp.json()       # first row is the header
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df = df.rename(columns=VARS)

    # Build the 11-char GEOID join key
    df["geoid"] = df["state"] + df["county"] + df["tract"]

    # API returns everything as strings; convert measures to numbers
    for col in VARS.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Census sentinel: large negative numbers (e.g. -666666666) mean "no data"
    df.loc[df["median_income"] < 0, "median_income"] = pd.NA
    return df

if __name__ == "__main__":
    df = fetch_acs()
    print("Tracts fetched:", len(df))
    print("GEOID lengths:", df["geoid"].str.len().unique())
    print(df[["geoid", "total_pop", "median_income"]].head())
    out = "data/raw/acs_worcester_2019.csv"
    df.to_csv(out, index=False)
    print("Saved ->", out)