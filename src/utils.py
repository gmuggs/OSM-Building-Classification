import os
import geopandas as gpd
import pandas as pd


def create_directory_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Directory '{path}' created successfully.")
    else:
        print(f"Directory '{path}' already exists.")


#Sandro's function
# https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.2023.html#list-tab-1883739534
# file: cb_2023_us_cbsa_500k.zip
def read_shapefile_regions(list_of_cbsas, path = "../data"):
    """Reads and returns a shapefile as a GeoDataFrame."""
    shapefile_path = os.path.join(path, "cb_2023_us_cbsa_500k","cb_2023_us_cbsa_500k.shp")
    gdf = gpd.read_file(shapefile_path)
    gdf["GEOID"] = gdf["GEOID"].astype(int)
    if len(list_of_cbsas) > 0:
        gdf = gdf[gdf["GEOID"].isin(list_of_cbsas)].reset_index(drop = True)
    return gdf


# All US. counties
# https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.2023.html#list-tab-1883739534
# file: cb_2023_us_county_500k 
def read_counties(path = "./data"):
    """Reads and returns a shapefile as a GeoDataFrame."""
    shapefile_path = os.path.join(path, "cb_2023_us_county_500k", "cb_2023_us_county_500k.shp")
    counties_gpf = gpd.read_file(shapefile_path)
    return counties_gpf


def get_counties_region(metropolitan_region, counties):
    counties = counties.to_crs(metropolitan_region.crs)
    overlap_gdf = gpd.sjoin(counties, metropolitan_region, how='inner', predicate='within')
    counties = overlap_gdf[['NAME_left','GEOID_left']]
    return counties


def get_utm_crs_from_geodataframe(gdf):
    """
    Determine the appropriate UTM CRS for a given GeoDataFrame.
    
    Parameters:
        gdf: GeoDataFrame with the input geometries
    
    Returns:
        utm_crs: The EPSG code for the appropriate UTM zone
    """
    # This function is based on Sec. 6.3 of https://bookdown.org/robinlovelace/geocompr/reproj-geo-data.html
    centroid = gdf.union_all().centroid
    lon, lat = centroid.x, centroid.y
    utm_zone = int((lon + 180) // 6) + 1 # Get the UTM zone
    hemisphere = 'north' if lat >= 0 else 'south'
    
    # Construct the EPSG code 
    if hemisphere == 'north':
        epsg_code = 32600 + utm_zone  
    else:
        epsg_code = 32700 + utm_zone
    
    return epsg_code
