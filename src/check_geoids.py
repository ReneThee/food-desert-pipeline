"""The same GEOIDs must exist in all three sources, or joins will lie."""
import pandas as pd
import geopandas as gpd

xl = pd.ExcelFile("data/raw/food_access_atlas_2019.xlsx")
sheet = [s for s in xl.sheet_names if "Atlas" in s][0]
usda = pd.read_excel("data/raw/food_access_atlas_2019.xlsx",
                     sheet_name=sheet, dtype={"CensusTract": str})
usda = usda[usda["State"].str.contains("Massachusetts", na=False)]
usda = usda[usda["County"].str.contains("Worcester", na=False)]
u = set(usda["CensusTract"])

acs = pd.read_csv("data/raw/acs_worcester_2019.csv", dtype={"geoid": str})
a = set(acs["geoid"])

tiger = gpd.read_file("zip://data/raw/tl_2019_25_tract.zip")
t = set(tiger.loc[tiger["COUNTYFP"] == "027", "GEOID"])

print(f"USDA: {len(u)}  ACS: {len(a)}  TIGER: {len(t)}")
print("In ACS but not USDA:", sorted(a - u))
print("In USDA but not ACS:", sorted(u - a))
print("In TIGER but not ACS:", sorted(t - a))