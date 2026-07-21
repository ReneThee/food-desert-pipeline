"""load MA tract geometries, filter to Worcester County, check CRS."""
import geopandas as gpd

# geopandas reads straight out of a zip
gdf = gpd.read_file("zip://data/raw/tl_2019_25_tract.zip")
print("MA tracts:", len(gdf), "| CRS:", gdf.crs)

wc = gdf[gdf["COUNTYFP"] == "027"].copy()
print("Worcester County tracts:", len(wc))
print("GEOID sample:", wc["GEOID"].head().tolist())

# Web maps (folium) want WGS84 lat/lon = EPSG:4326
wc = wc.to_crs(epsg=4326)
print("Reprojected CRS:", wc.crs)
print("Bounds (should be ~ -72.3..-71.4 lon, 42.0..42.7 lat):", wc.total_bounds)