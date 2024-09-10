import geopandas as gpd
import pickle
from shapely.ops import unary_union
import os
import sys
homedir = "../"
codedir = os.path.join(homedir, 'src')
sys.path.append(codedir)
from utils import create_directory_if_not_exists
from shapely.geometry import MultiPolygon
import pandas as pd

#Save all necessary files in a pickle file to be used by validation.py
def save(name2gdf, path):
    with open(os.path.join(path,'test_region2gdf.pickle'), 'wb') as handle:
        pickle.dump(name2gdf, handle, protocol=pickle.HIGHEST_PROTOCOL)


def remove_overlapping_parts(gdf, multi_polygon):
    new_geometries = []
    indices = []

    for idx, row in gdf.iterrows():
        geom = row.geometry
        difference_geom = geom.difference(multi_polygon)
        if not difference_geom.is_empty:
            new_geometries.append(difference_geom)
            indices.append(idx)

    result_gdf = gdf.loc[indices].copy()
    result_gdf.geometry = new_geometries
    return result_gdf


def remove_overlapping_mixed(gdf_in):
    gdf = gdf_in.copy()
    gdf = gdf[gdf.is_valid]

    gdf = gdf.explode(index_parts=False) #return as polygons
    gdf.reset_index(drop=True, inplace=True)# Reset the index to avoid any issues

    unique_types = gdf['org_type'].unique()
    # utype2merged_geometry = dict()
    compare_with = {
        "RES": "NON_RES",
        "NON_RES": "RES",
    }

    gdfs = []
    for utype in unique_types:
        subset = gdf[gdf['org_type'] == utype].copy() # Select footprints of the current type
        multi_polygon = unary_union(subset['geometry']) #It is now a single multi polygon
        #Remove overlapping with the opposite type
        gdfs.append(remove_overlapping_parts(gdf[gdf['org_type'] == compare_with[utype]], multi_polygon))
    gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
    
    gdf = gdf.explode(index_parts=False) #return as polygons
    gdf.reset_index(inplace=True, drop=True)
    return gdf


def redefine_categories(old2new_category, col_name, shapefile_path):
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.dropna(subset=['geometry'])
    gdf = gdf[gdf.geometry.geom_type != 'Point']
    gdf = gdf[gdf.geometry.geom_type != 'LineString']
    gdf.dropna(subset=[col_name], inplace = True)
    gdf.reset_index(inplace=True, drop=True)
    gdf['old_label'] = gdf[col_name]
    gdf = gdf.rename(columns={col_name: 'org_type',})
    org_type = [old2new_category[t] for t in gdf['org_type']]
    gdf['org_type'] = org_type
    drop_list = ["N/A"]
    gdf.drop(gdf[(gdf['org_type'].isin(drop_list))].index, inplace = True)
    gdf.reset_index(inplace=True, drop=True)
    gdf = gdf.explode(index_parts=False) #return as polygons
    gdf.reset_index(drop=True, inplace=True)# Reset the index to avoid any issues
    return remove_overlapping_mixed(gdf)


in_path = "../raw_data/"
out_path = "../data/"
create_directory_if_not_exists(out_path)

name2gdf = dict()

print("Fairfax, VA")
#Merge files
# https://www.fairfaxcounty.gov/maps/open-geospatial-data
shapefile_path = os.path.join(in_path, "Existing_Land_Use_-_Generalized", "Existing_Land_Use_-_Generalized.shp")
county = gpd.read_file(shapefile_path)

delete_columns = ['ACRES', 'VALID_FROM', 'VALID_TO', 'Shape__Are', 'Shape__Len', 'OBJECTID']
county.drop(columns=delete_columns, inplace=True)
county.rename(columns={'CATEG': 'TYPE'}, inplace=True)

# https://data-cityoffairfax.opendata.arcgis.com/
shapefile_path = os.path.join(in_path,"Land_Use_Existing_-2984936049164631990", "Land_Use_Existing.shp")
city = gpd.read_file(shapefile_path)

delete_columns = ['OBJECTID_1', 'PIN', 'Secondary', 'SHAPE_STAr', 'SHAPE_STLe','GlobalID']
city.drop(columns=delete_columns, inplace=True)

city.rename(columns={'ELU': 'TYPE'}, inplace=True)

city = city.to_crs(county.crs)
city = city[city['TYPE'] != 'NONE']
city.reset_index(inplace=True, drop=True)

merged = pd.concat([city, county], axis=0)
merged.reset_index(inplace=True, drop=True)
create_directory_if_not_exists(os.path.join(in_path, "fairfax"))
merged.to_file(os.path.join(in_path, "fairfax", "fairfax.shp"))


#Process merged file
TYPE2category = {
    'High-density Residential': 'RES',
    'Low-density Residential': 'RES',
    'Medium-density Residential': 'RES',
    'Agricultural': 'N/A',
    'Commercial': 'NON_RES',
    'Industrial, light and heavy': 'NON_RES',
    'Institutional': 'NON_RES',
    'Open land, not forested or developed': 'N/A',
    'Public': 'NON_RES',
    'Recreation': 'NON_RES', #N/A?
    'Surface water': 'N/A',
    'Utilities': 'N/A',
    'Industrial': 'NON_RES',
    'Institutional - General': 'NON_RES',
    'Institutional - Government': 'NON_RES',
    'Mixed-Use Residential/Commercial': 'N/A', #there are just two buildings like this 
    'Open Space - Private': 'N/A',
    'Open Space - Public': 'N/A',
    'Residential - Multifamily': 'RES',
    'Residential - Single Attached': 'RES',
    'Residential - Single Detached': 'RES',
    'Vacant': 'N/A',
    None: 'N/A',
}
col_name = "TYPE"
folder_name = "fairfax"
file_name = "fairfax.shp"
shapefile_path = os.path.join(in_path, folder_name, file_name)
gdf = redefine_categories(TYPE2category, col_name, shapefile_path)
name2gdf['Fairfax'] = gdf


print("Boulder, CO")
BLDGTYPE2category = {
    'Agricultural':"N/A",
    'Commercial': "NON_RES",
    'Foundation/Ruin':"N/A",
    'Garage/Shed':"N/A",
    'Industrial': "NON_RES",
    'Medical': "NON_RES",
    'Misc':"N/A",
    'Parking Structure':"N/A",
    'Public': "NON_RES",
    'Public Safety': "NON_RES",
    'Religious': "NON_RES",
    'Residential': 'RES',
    'School': "NON_RES",
    'Tank':"N/A",
}
col_name = "BLDGTYPE"
folder_name = "Boulder_admin_buildings"
file_name = "Boulder_admin_buildings.shp"

shapefile_path = os.path.join(in_path, folder_name, file_name)
gdf = redefine_categories(BLDGTYPE2category, col_name, shapefile_path)
name2gdf['Boulder'] = gdf


print("Mecklenburg, NC")
# col_name = "descproper"
# folder_name = "Mecklenburg_admin_buildings"
# file_name = "Mecklenburg_admin_buildings.shp"
# https://maps.mecknc.gov/openmapping/data.html
# Tax Parcel Landuse Existing
landuse_de2category = {
    '100 YEAR FLOOD PLAIN - AC':"N/A",
    '100 YEAR FLOOD PLAIN - LT':"N/A",
    'AGRICULTURAL - COMMERCIAL PRODUCTION':"N/A",
    'AIR RIGHTS PARCEL':"N/A",
    'AIRPORT':"NON_RES",
    'AUTO SALES AND SERVICE':"NON_RES",
    'BANK':"NON_RES",
    'BILL BOARD':"N/A",
    'BUFFER STRIP':"N/A",
    'CAR WASH':"NON_RES",
    'CELL TOWER':"NON_RES",
    'CHURCH':"NON_RES",
    'CLUB, LODGES, UNION HALL, SWIM CLUB':"NON_RES",
    'COLLEGE - PUBLIC':"NON_RES",
    'COMMERCIAL':"NON_RES",
    'COMMERCIAL COMMON AREA':"NON_RES",
    'COMMERCIAL CONDOMINIUM':"NON_RES",
    'COMMERCIAL CONDOMINIUM COMMON AREA':"NON_RES",
    'COMMERCIAL SERVICE(LAUNDRY,TV,RADIO,ETC)':"NON_RES",
    'COMMERCIAL WATER FRONTAGE':"NON_RES",
    'CONDO AFFORDABLE HOUSING':"RES",
    'CONDOMINIUM':"RES",
    'CONDOMINIUM COMMON AREA':"RES",
    'CONDOMINIUM HIGH RISE':"RES",
    'CONDOMINIUM WATER FRONTAGE':"RES",
    'CONDOMINIUM WATER VIEW':"RES",
    'CONSERVATION - AGRICULTURAL COMM':"N/A",
    'CONSERVATION - FORESTRY COMM':"N/A",
    'CONSERVATION - WILDLIFE':"N/A",
    'CONSERVATION - WOODLAND EXCESS AC':"N/A",
    'CONVENIENCE STORE':"NON_RES",
    'CONVIENCE/FAST FOOD STORE':"NON_RES",
    'COUNTRY CLUB':"NON_RES",
    'DAY CARE CENTER':"NON_RES",
    'DEPARTMENT STORE':"NON_RES",
    'ENVIRONMENTAL HAZARD':"NON_RES",
    'FAST FOOD':"NON_RES",
    'FIRE DEPARTMENT':"NON_RES",
    'FLUM/SWIM FLOODWAY (NO BUILD ZONE)':"N/A",
    'FOREST - COMMERCIAL PRODUCTION':"N/A",
    'FUNERAL (MORTUARY, CEMETERY, CREMATORIUM, MAUS)':"NON_RES",
    'GOLF COURSE CLASS 1 - CHAMPIONSHIP':"NON_RES",
    'GOLF COURSE CLASS 2 - PRIVATE CLUB':"NON_RES",
    'GOLF COURSE CLASS 3 - SEMI-PRIVATE & MUNICIPAL':"NON_RES",
    'GOLF COURSE CLASS 4 - MINIMUM QUALITY':"NON_RES",
    'GREENWAY TRAIL':"N/A",
    'HABITAT FOR HUMANITY':"N/A",
    'HOME FOR THE AGED':"RES",
    'HORTICULTURAL - COMMERCIAL PRODUCTION':"N/A",
    'HOSPITAL, PRIVATE':"NON_RES",
    'HOSPITALS - PUBLIC':"NON_RES",
    'HOTEL/MOTEL < 7 FLOORS':"NON_RES",
    'HOTEL/MOTEL > 6 FLOORS':"NON_RES",
    'INDUSTRIAL':"NON_RES",
    'INDUSTRIAL COMMON AREA':"NON_RES",
    'INDUSTRIAL PARK':"NON_RES",
    'INSTITUTIONAL':"NON_RES",
    'ISLAND':"N/A",
    'LABORATORY / RESEARCH':"NON_RES",
    'LEASEHOLD INTEREST':"NON_RES",
    'LIGHT MANUFACTURING':"NON_RES",
    'LUMBER YARD':"NON_RES",
    'MARINA LAND':"NON_RES",
    'MEDICAL CONDOMINIUM':"NON_RES",
    'MEDICAL CONDOMINIUM COMMON AREA':"NON_RES",
    'MEDICAL OFFICE':"NON_RES",
    'MINI WAREHOUSE':"NON_RES",
    'MINIATURE GOLF COURSES/DRIVING RANGE':"NON_RES",
    'MINING':"N/A",
    'MOBILE HOME HS':"RES",
    'MOBILE HOME PARK':"N/A",
    'MOBILE HOME SUBDIVISION':"N/A",
    'MULTI FAMILTY AFFORDABLE HOUSING':"RES",
    'MULTI FAMILY':"RES",
    'MULTI FAMILY COMMON AREA':"RES",
    'MULTI FAMILY DUPLEX/TRIPLEX':"RES",
    'MULTI FAMILY GARDEN':"N/A",
    'MULTI FAMILY HIGH RISE':"RES",
    'MULTI FAMILY TOWNHOUSE':"RES",
    'MULTI FAMILY WATER ACCESS':"N/A",
    'MUNICIPAL AIRPORT':"NON_RES",
    'MUNICIPAL EDUCATION':"NON_RES",
    'NEW PARCEL':"N/A",
    'NO LAND INTEREST':"N/A",
    'NURSING HOME':"RES",
    'OFFICE':"NON_RES",
    'OFFICE CONDOMINIUM':"NON_RES",
    'OFFICE CONDOMINIUM COMMON AREA':"NON_RES",
    'OFFICE HIGH RISE - > 6 STORIES':"NON_RES",
    'OTHER COUNTY PROPERTY':"NON_RES",
    'OTHER FEDERAL':"NON_RES",
    'OTHER MUNICIPAL':"NON_RES",
    'PACKING PLANT':"NON_RES",
    'PARKING':"N/A",
    'PATIO HOME':"N/A",
    'PATIO HOME - WATERFRONT':"N/A",
    'PETROLEUM AND GAS':"N/A",
    'PVT Owned RR with Rail ROW':"N/A",
    'R101':"N/A",
    'REC AREA':"N/A",
    'RESERVED PARCEL':"N/A",
    'RESIDENTIAL AFFORDABLE HOUSING':"RES",
    'RESTAURANT':"NON_RES",
    'RIGHT OF WAY':"N/A",
    'ROADWAY CORRIDOR':"N/A",
    'RURAL HOMESITE':"N/A",
    'SCHOOL - PUBLIC':"NON_RES",
    'SCHOOL,COLLEGE, PRIVATE':"NON_RES",
    'SERVICE GARAGE':"NON_RES",
    'SERVICE STATION':"NON_RES",
    'SHOPPING CENTER - MALL':"NON_RES",
    'SHOPPING CENTER - STRIP':"NON_RES",
    'SINGLE FAMILY RESIDENTIAL':"RES",
    'SINGLE FAMILY RESIDENTIAL - ACREAGE':"RES",
    'SINGLE FAMILY RESIDENTIAL - COMMON':"RES",
    'SINGLE FAMILY RESIDENTIAL - GOLF':"RES",
    'SINGLE FAMILY RESIDENTIAL - RIVER':"RES",
    'SINGLE FAMILY RESIDENTIAL - WATER VIEW':"RES",
    'SINGLE FAMILY RESIDENTIAL - WATERFRONT':"RES",
    'SINGLE FAMILY RESIDENTIAL GATED COMMUNITY':"RES",
    'SINGLE FAMILY RESIDENTIAL MINI FARM/ESTATE':"RES",
    'STATE PROP':"N/A",
    'SUBMERGED LAND, RIVERS AND LAKES':"N/A",
    'SUPERMARKET':"NON_RES",
    'TOWN HOUSE  GOLF COURSE FRONTAGE':"RES",
    'TOWN HOUSE  SFR':"RES",
    'TOWN HOUSE  WATER ACCESS':"RES",
    'TOWN HOUSE  WATER FRONTAGE':"RES",
    'TOWN HOUSE COMMON AREA':"RES",
    'TOWNHOUSE AFFORDABLE HOUSING':"RES",
    'TRUCK TERMINAL':"NON_RES",
    'UNSUITABLE FOR SEPTIC':"N/A",
    'USE VALUE HOMESITE':"N/A",
    'UTILITY (GAS, ELECTRIC, TELEPHONE, TELEGRAPH, RAIL':"N/A",
    'UTILITY EASEMENT':"N/A",
    'UTILITY/P':"N/A",
    'WAREHOUSE CONDOMINIUM':"NON_RES",
    'WAREHOUSE CONDOMINIUM COMMON AREA':"NON_RES",
    'WAREHOUSING':"NON_RES",
    'WASTELAND, SLIVERS, GULLIES, ROCK OUTCROP': "N/A",
    'WATER PLANT':"N/A",
    'WATER RETENTION POND':"N/A",
    'WELL LOT': "N/A",
    'WETLAND':"N/A",
    'WOODLAND - EXCESS ON AG PCL':"N/A",
}
col_name = "landuse_de"
folder_name = "Mecklenburg_admin_buildings_new"
file_name = "Parcel_Landuse.shp"
shapefile_path = os.path.join(in_path, folder_name, file_name)
gdf = redefine_categories(landuse_de2category, col_name, shapefile_path)
name2gdf['Mecklenburg'] = gdf


print("Hanover, VA")
# https://parcelmap.hanovercounty.gov/#
ZONING_LIS2category = {
    'A-1': "N/A", # agriculture or horticulture
    'AR-1': "N/A", # agriculture residential district
    'AR-2': "N/A", # agriculture residential district
    'AR-6': "N/A", # agriculture residential district
    'B-1': "NON_RES", # business and industrial
    'B-2': "NON_RES", # business and industrial
    'B-3': "NON_RES", # business and industrial
    'B-4': "NON_RES", # business and industrial
    'B-O': "NON_RES", # business and industrial
    'HE': "N/A", # Highway Corridor Overlay District
    'M-1': "NON_RES", # Limited Industrial
    'M-2': "NON_RES", # Light Industrial
    'M-3': "NON_RES", # Heavy Industrial
    'MX': "N/A", # Mixed
    'O-S': "NON_RES", # Opens Sapce
    'PMH': "RES", #Planned Mobile Home
    'PSC': "NON_RES", #Planned Shopping Center
    'PUD': "N/A", #Planned Unit Development (mix)
    'R-1': "RES", # single family
    'R-2': "RES", # single family
    'R-3': "RES", # single family
    'R-4': "RES", # residential cluster development district
    'R-5': "RES", # multiple-family residential district
    'R-6': "RES", # residential mobile homes
    'RC': "N/A", # "NON_RES", #Rural Conservation 
    'RM': "RES", # Residential Multifamily
    'RO-1': "N/A", # residential-office (mix)
    'RR-1': "N/A", # "RES", # Rural Residential
    'RRC': "N/A", # "RES", # Rural Residential Cluster
    'RS': "RES", # Single-Family Residential
    'See Map': "N/A",
    None: "N/A",
}
col_name = "ZONING_LIS"
folder_name = "Hanover_Parcels_-1335205000025218776"
file_name = "Hanover_Parcels.shp"
shapefile_path = os.path.join(in_path, folder_name, file_name)
gdf = redefine_categories(ZONING_LIS2category, col_name, shapefile_path)
name2gdf['Hanover'] = gdf


print("Baltimore County, MD") # No baltimore city
# https://opendata.baltimorecountymd.gov/datasets/e45bd5ad0de14bf988f825dd7a4431af_0/explore?location=39.452147%2C-76.611050%2C10.00
# Updated September 19, 2023
GIS_LU_COD2category = {
    'AGRICULTURAL VACANT': "N/A",
    'AGRICULTURE': "N/A",
    'AIRPORT': "NON_RES",
    'ASSISTED LIVING FACILITY': "N/A",
    'CEMETARY W/O PLACE OF WORSHIP': "N/A",
    'COLLEGE': "NON_RES",
    'COMMERCIAL': "NON_RES",
    'COUNTY OPEN SPACE': "N/A",
    'COUNTY PARK': "N/A",
    'COUNTY SENIOR CENTER': "N/A",
    'ELECTRIC, GAS, TELECOMMUNICATIONS UTILITY': "N/A",
    'FIRE FACILITY': "NON_RES",
    'FURTHER REVIEW': "N/A",
    'HOA/COA/DEVELOPER/MULTIFAMILY MGMT': "RES",
    'HOSPITAL': "NON_RES",
    'INDUSTRIAL': "NON_RES",
    'LANDFILL': "N/A",
    'LIBRARY': "NON_RES",
    'MISC. GOVERNMENT-PUBLIC': "NON_RES",
    'MISC. INSTITUTION-PRIVATE': "NON_RES",
    'MIXED OFFICE/INDUSTRIAL': "NON_RES",
    'MIXED OFFICE/INDUSTRIAL/RETAIL': "NON_RES",
    'MIXED OFFICE/RETAIL': "NON_RES",
    'MIXED RESIDENTIAL/OFFICE/RETAIL': "N/A",
    'MULTI SFD': "RES",
    'MULTIFAMILY': "RES",
    'NON-COUNTY PARCEL': "RES",
    'OFFICE': "NON_RES",
    'OTHER GOVERNMENT OPEN SPACE': "N/A",
    'OTHER PRIVATE OPEN SPACE': "N/A",
    'OTHER PUBLIC PARK': "N/A",
    'PARK AND RIDE': "N/A",
    'PERMANENT EASEMENT': "N/A",
    'PIPELINE': "N/A",
    'PLACE OF WORSHIP': "N/A",
    'POLICE FACILITY': "NON_RES",
    'PRIVATE SCHOOL': "NON_RES",
    'PRIVATELY OWNED GOLF COURSE': "NON_RES",
    'PUBLIC SCHOOL OR SCHOOL SITE': "NON_RES",
    'PUBLICLY OWNED GOLF COURSE': "NON_RES",
    'RAIL': "N/A",
    'RESERVOIR PROPERTY': "N/A",
    'ROAD': "N/A",
    'RURAL RESIDENTIAL SFD': "N/A",
    'SFA': "RES",
    'SFD': "RES",
    'SFSD': "RES",
    'STATE PARK': "N/A",
    'STORM DRAINAGE': "N/A",
    'UNBUILDABLE/ENVIRONMENTALLY CONSTRAINED': "N/A",
    'VACANT': "N/A",
    'WATER': "N/A",
    'WATER OR SEWER UTILITY': "N/A",
}
col_name = "GIS_LU_COD"
folder_name = "baltimore"
file_name = "Landuse.shp"
shapefile_path = os.path.join(in_path, folder_name, file_name)
gdf = redefine_categories(GIS_LU_COD2category, col_name, shapefile_path)
name2gdf['Baltmore'] = gdf


# Seven county Twin Cities (Minneapolis and St. Paul) Metropolitan Area in Minnesota (MN)
# Generalized Land Use 2020
# https://gisdata.mn.gov/dataset/us-mn-state-metc-plan-generl-lnduse2020
DESC20202category = {
    'Agricultural': "N/A",
    'Airport or Airstrip': "NON_RES",
    'Extractive': "N/A",
    'Farmstead': "N/A",
    'Golf Course': "NON_RES",
    'Industrial or Utility': "NON_RES",
    'Institutional': "NON_RES",
    'Major Highway': "N/A",
    'Major Railway': "N/A",
    'Manufactured Housing Park': "RES",
    'Mixed Use Commercial': "NON_RES", #Land containing a building with multiple uses but with NO residential units or industrial uses.
    'Mixed Use Industrial': "NON_RES", #Land containing a building with multiple uses in combination with industrial uses and NO residential units. An example would be a building containing a warehouse, offices, and stores.
    'Mixed Use Residential': "N/A", #Mixed use
    'Multifamily': "RES",
    'Office': "NON_RES",
    'Open Water': "N/A",
    'Park, Recreational, or Preserve': "N/A",
    'Retail and Other Commercial': "NON_RES",
    'Seasonal/Vacation': "N/A", #Land meeting the general definition of single-family residential containing a dwelling unit occupied seasonally or used as vacation property
    'Single Family Attached': "RES",
    'Single Family Detached': "RES",
    'Undeveloped': "N/A",
}
col_name = "DESC2020"
folder_name = "Metropolitan_reg_Minneapolis_and_St_Paul"
file_name = "GeneralizedLandUse2020.shp"
shapefile_path = os.path.join(in_path, folder_name, file_name)
buildings_gdf = redefine_categories(DESC20202category, col_name, shapefile_path)


# Load auxilyary GeoDataFrames
counties_gdf = gpd.read_file(os.path.join(in_path, "cb_2023_us_county_500k", "cb_2023_us_county_500k.shp"))

# Ensure both GeoDataFrames have the same CRS
if buildings_gdf.crs != counties_gdf.crs:
    buildings_gdf = buildings_gdf.to_crs(counties_gdf.crs)

# Perform a spatial join to segment buildings by counties
buildings_by_county = gpd.sjoin(buildings_gdf, counties_gdf, how='inner', predicate='within')

counties = {'Carver', 'Dakota', 'Scott', 'Hennepin', 'Ramsey', 'Washington', 'Anoka',}

for county in counties:
    gdf_county = buildings_by_county[buildings_by_county['NAME']==county]
    name2gdf[f'{county}_MN'] = gdf_county

save(name2gdf, out_path)


# def extract_polygons(geom):
#     """Extract Polygons and MultiPolygons from a GeometryCollection."""
#     if geom.geom_type == 'GeometryCollection':
#         polygons = [g for g in geom.geoms if g.geom_type in ['Polygon', 'MultiPolygon']]
#         return MultiPolygon(polygons) if len(polygons) > 0 else None
#     return geom

# for name in name2gdf.keys():
#     gdf = name2gdf[name]
#     gdf['geometry'] = gdf['geometry'].apply(extract_polygons)
#     gdf = gdf[gdf.geometry.geom_type != 'LineString']
#     gdf = gdf[gdf.geometry.geom_type != 'MultiLineString']
#     gdf['geometry'] = gdf['geometry'].apply(lambda geom: MultiPolygon([geom]) if geom.geom_type == 'Polygon' else geom)
#     gdf.reset_index(inplace=True, drop=True)
#     gdf.to_file(os.path.join(out_path, "gdfs/{name}.shp") 
