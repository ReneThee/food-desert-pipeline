
import pandas as pd

PATH = "data/raw/food_access_atlas_2019.xlsx"

xl = pd.ExcelFile(PATH)
print("Sheets:", xl.sheet_names)

sheet = [s for s in xl.sheet_names if "Atlas" in s][0]

# CensusTract must be read as a string since it is a GEOID.
df = pd.read_excel(PATH, sheet_name=sheet, dtype={"CensusTract": str})
print("Shape (all US):", df.shape)

ma = df[df["State"].str.contains("Massachusetts", case=False, na=False)]
print("County spellings in MA:", sorted(ma["County"].unique())[:20])

# filter to Worcester County
wc = ma[ma["County"].str.contains("Worcester", case=False, na=False)].copy()
print("Worcester County tracts:", len(wc))
print("GEOID sample:", wc["CensusTract"].head().tolist())
print("GEOID lengths:", wc["CensusTract"].str.len().unique())

# confirm the columns we care about exist
wanted = ["CensusTract", "Urban", "Pop2010", "OHU2010", "PovertyRate",
          "MedianFamilyIncome", "LILATracts_1And10", "LowIncomeTracts",
          "lapop1share", "lapop10share", "TractSNAP", "TractHUNV"]
missing = [c for c in wanted if c not in wc.columns]
print("Missing columns:", missing if missing else "none — all present")
print(wc[[c for c in wanted if c in wc.columns]].describe())