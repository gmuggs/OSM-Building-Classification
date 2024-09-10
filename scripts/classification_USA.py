import os
import sys
homedir = "../"
codedir = os.path.join(homedir, 'src')
sys.path.append(codedir)
import map_buildings, utils

from shapely.geometry import MultiPolygon, Polygon
# import pickle
import osmnx as ox
import pandas as pd

in_path = "../raw_data/"
out_path = "../out/"
cache_folder = "../osmnx_cache/"

ox.settings.cache_folder = cache_folder
ox.settings.requests_timeout = 500


# https://www.census.gov/data/tables/time-series/demo/popest/2020s-total-metro-and-micro-statistical-areas.html
# Annual Resident Population Estimates and Estimated Components of Resident Population Change for Metropolitan and Micropolitan Statistical Areas and Their Geographic Components for the United States: April 1, 2020 to July 1, 2023 (CBSA-EST2023-ALLDATA) [< 1.0 MB]
# File: cbsa-est2023-alldata.csv
csv_path = os.path.join(in_path,"cbsa-est2023-alldata.csv")
df = pd.read_csv(csv_path, encoding='latin1')
df_metropolitan = df[df['LSAD'] == "Metropolitan Statistical Area"]
df_micropolitan = df[df['LSAD'] == "Micropolitan Statistical Area"]
metropolitan_cbsa = set(df_metropolitan['CBSA'])
micropolitan_cbsa = set(df_micropolitan['CBSA'])

df_county = df[df['LSAD'] == "County or equivalent"]
metropolitan_county_id = df[df['CBSA'].isin(metropolitan_cbsa)]['STCOU']
metropolitan_county_id = metropolitan_county_id[metropolitan_county_id.notna()].astype(int)

micropolitan_county_id = df[df['CBSA'].isin(micropolitan_cbsa)]['STCOU']
micropolitan_county_id = micropolitan_county_id[micropolitan_county_id.notna()].astype(int)

metropolitan_county_id = set(metropolitan_county_id)
micropolitan_county_id = set(micropolitan_county_id)

df_aux = df_county[df_county['STCOU'].notnull()]
df_aux['STCOU'] = df_aux['STCOU'].astype(int)
county_id2cbsa = df_aux.set_index('STCOU')['CBSA'].to_dict()

all_counties = utils.read_counties(in_path)

county_id2folder = dict()
county_id2file_name = dict()
county_id2pickle_name = dict()
for index in all_counties.index:
    county = all_counties.loc[index]
    geoid = int(county['GEOID'])
    name = f"{county['NAME']} {county['STUSPS']}"
    name = name.replace(".","_").replace(" ","_")
    region_type = "other"
    if geoid in metropolitan_county_id:
        region_type = os.path.join('metropolitan', str(county_id2cbsa[geoid]))
    elif geoid in micropolitan_county_id:
        region_type = os.path.join('micropolitan', str(county_id2cbsa[geoid]))

    partial_path = os.path.join(out_path,region_type)
    county_id2folder[geoid] = partial_path
    name_out = f"{geoid}_{name}.shp"
    path_out = os.path.join(partial_path,name_out)
    county_id2file_name[geoid] = path_out
    name_out = f"{geoid}_{name}.pickle"
    path_out = os.path.join(partial_path,name_out)
    county_id2pickle_name[geoid] = path_out


all_counties['GEOID'] = all_counties['GEOID'].astype(int)
num_segments = 5
numeber_of_counties = len(all_counties.index)
for i, county_i in enumerate(all_counties.index):
    county = all_counties.loc[county_i]
    name = f"{county['NAME']} {county['STUSPS']}"
    print(f"{name}: {i+1} of {numeber_of_counties}")
    county_geoid = int(county['GEOID'])
    utils.create_directory_if_not_exists(county_id2folder[county_geoid])

    filename_out = county_id2file_name[county_geoid]
    polygon = all_counties[all_counties['GEOID'] == county_geoid].iloc[0].geometry
    gdf_identified, footprint_id2features, gdf_not_used = map_buildings.generate_gdf_with_segments(polygon, num_segments, map_buildings.tags) # Keep in mind that tags on OSMnx are keys in OSM.
    gdf_identified['geometry'] = gdf_identified['geometry'].apply(lambda geom: MultiPolygon([geom]) if isinstance(geom, Polygon) else geom)
    gdf_identified = gdf_identified[gdf_identified.geometry.type != 'Point']
    gdf_identified = gdf_identified[gdf_identified.geometry.type != 'LineString']

    # Convert all to the utm_crs 
    utm_crs = utils.get_utm_crs_from_geodataframe(gdf_identified)
    gdf_identified = gdf_identified.to_crs(epsg=utm_crs) 

    if gdf_identified.shape[0] > 0:
        gdf_identified.index = pd.MultiIndex.from_tuples(gdf_identified.index, names=['el_type', 'osmid'])
    
    gdf_identified = map_buildings.use_auxiliary_data(gdf_identified, footprint_id2features)
    print(f"Saving: {filename_out}")
    gdf_identified.to_file(filename_out)

    # This code can be used to save all of the auxiliary data.
    # filename_auxiliary_data_out = county_id2pickle_name[county_geoid]
    # print(f"Saving: {filename_auxiliary_data_out}")
    # with open(filename_auxiliary_data_out, 'wb') as handle:
    #     pickle.dump(footprint_id2features, handle, protocol=pickle.HIGHEST_PROTOCOL)
