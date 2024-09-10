import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
import networkx as nx
import igraph as ig
import pandas as pd
from collections import Counter
import geopandas as gpd
from tqdm import tqdm
import re 
from matplotlib import colors
from shapely.geometry import Polygon
from collections import OrderedDict
import geopandas as gpd
from shapely.geometry import Polygon


ox.io.settings.max_query_area_size = 50000000000

#All accomodations are from: https://wiki.openstreetmap.org/wiki/Map_features#Accommodation
residential_types = {
    "apartments",
    "barracks",
    "bungalow",
    "cabin",
    "detached",
    "dormitory",
    "farm",
    "ger",
    "house",
    "houseboat",
    "residential",
    "semidetached_house",
    "static_caravan",
    "stilt_house",
    "terrace",
    "tree_house",
    "trullo",
    "townhouse",
    "townhome",
    "boathouse",
    "shed",
    # "hotel",#hotel is not residential
    'garage', 
    'garages', #A building that consists of a number of discrete storage spaces for different owners/tenants.
}


tags = {'building': True, 
        'surface':True, #do not use (just to avoid errors)
        'amenity':True, 
        'emergency':True,
        'healthcare':True,
        'landuse':True, #
        'military':True,
        'office':True,
        'public_transport':True,
        'service':True,
        'shop':True,
        'sport':True,
        'telecom':True,
        'tourism':True,
        'brand':True,
        'clothes':True,
        'leisure':True,
        'cemetery':True,
        }

#Amenities were considered before
to_non_residential = {'emergency','healthcare','landuse','military','office','public_transport','service','shop','sport','telecom', 'tourism', 'brand','clothes', 'leisure', 'cemetery'}

tags_do_not_consider = {'construction', 'driveway', 'grass', 'farmyard', 'farmland', 'farmyard', 'grass', 'nature_reserve'}

#It is ordered because the order is important
col2residential_type = OrderedDict()
col2residential_type['landuse'] = ['residential']
col2residential_type['tourism'] = ['apartment', #We expect that apaprtments are in residential buildings
                                   'guest_house',
                                  ]

col2non_residential_type = OrderedDict()
col2non_residential_type['landuse'] = ['commercial', 
                                        'retail', 
                                        'industrial', 
                                        'institutional', 
                                        'education', 
                                        'military', 
                                        'port',
                                        'religious',
                                        'winter_sports',
                                        'cemetery', 
                                        'grave_yard',
                                      ]


col2non_residential_type['amenity'] = ['courthouse',
                                       'fire_station',
                                       'police',
                                       'post_depot',
                                       'post_office',
                                       'prison',
                                       'ranger_station',
                                       'townhall',
                                       'college', 
                                       'kindergarten',
                                       'library',
                                       'research_institute',
                                       'school',
                                       'university',
                                       'car_rental',
                                       'car_wash',
                                       'vehicle_inspection',
                                       'ferry_terminal',
                                       'fuel',
                                       'hospital',
                                       'brothel',
                                       'casino',
                                       'cinema',
                                       'conference_centre',
                                       'events_venue',
                                       'exhibition_centre',
                                       'love_hotel',
                                       'nightclub',
                                       'planetarium',
                                       'theatre',
                                       'bar',
                                       'restaurant',
                                      ]

col2skip_type = dict()
col2skip_type['landuse'] = {'forest',
                           }

col2skip_type['leisure'] = {'park',
                            'swimming_pool',
                           }

unknown = {'yes',
           'service', #service can be both
           'roof',
           'ruins',
           'construction'} 


def _define_type(gdf_in):
    gdf = gdf_in.copy()
    gdf['building'] = gdf['building'].str.lower() #to avoid mistakes
    gdf_out_list = []

    tags_used = list(set(tags.keys()).intersection(gdf.columns))
    tags_used.remove('building')
    if 'surface' in tags_used:
        tags_used.remove('surface')

    gdf_residential = gdf[gdf['building'].isin(residential_types)]
    tag_used_gdf = gdf_residential['building'].copy()
    gdf_residential = gdf_residential[['geometry']]
    gdf_residential['type'] = 'RES'
    gdf_residential['aux info'] = 'residential_types'
    gdf_residential['tag used'] = [f"building:{t}" for t in tag_used_gdf]
    gdf_out_list.append(gdf_residential.copy())

    gdf = gdf.drop(gdf_residential.index)

    #Add other residential tags
    for col in col2residential_type.keys():
        if col in gdf:
            gdf[col] = gdf[col].str.lower()
            gdf_residential = gdf[gdf[col].isin(col2residential_type[col])]
            tag_used_gdf = gdf_residential['building'].copy()
            gdf_residential = gdf_residential[['geometry']]
            gdf = gdf.drop(gdf_residential.index)
            gdf_residential['type'] = 'RES'
            gdf_residential['aux info'] = 'residential_types'
            gdf_residential['tag used'] = [f"building:{t}" for t in tag_used_gdf]
            gdf_out_list.append(gdf_residential.copy())

    gdf_non_residential = gdf[gdf['building'].notna()]
    gdf_non_residential = gdf_non_residential[~gdf_non_residential['building'].isin(unknown)]
    tag_used_gdf = gdf_non_residential['building'].copy()
    gdf_non_residential = gdf_non_residential[['geometry']]
    gdf_non_residential['type'] = 'NON_RES'
    gdf_non_residential['aux info'] = 'non_residential_types'
    gdf_non_residential['tag used'] = [f"building:{t}" for t in tag_used_gdf]
    gdf = gdf.drop(gdf_non_residential.index)
    gdf_out_list.append(gdf_non_residential.copy())

    #Add other non residential tags
    for col in col2non_residential_type.keys():
        if col in gdf:
            gdf[col] = gdf[col].str.lower()
            gdf_non_residential = gdf[gdf[col].isin(col2non_residential_type[col])]
            if gdf_non_residential.shape[0] > 0:
                tag_used_gdf = gdf_non_residential[col].copy()
                gdf_non_residential = gdf_non_residential[['geometry']]
                gdf = gdf.drop(gdf_non_residential.index)
                gdf_non_residential['type'] = 'NON_RES'
                gdf_non_residential['aux info'] = 'non_residential_types'
                gdf_non_residential['tag used'] = [f"{col}:{t}" for t in tag_used_gdf]
                gdf_out_list.append(gdf_non_residential.copy())

    # Taking a look at aditional tags (not used before in this function)
    tags_to_be_used = tags_used.copy()
    for col in set(list(col2non_residential_type.keys()) + list(col2residential_type.keys())):# not used tags
        if col in tags_to_be_used:
            tags_to_be_used.remove(col)

    # gdf_non_residential_aux = gdf[gdf[tags_to_be_used].notna().any(axis=1)]
    for tag_to_be_used in tags_to_be_used:
        gdf_non_residential = gdf[gdf[tag_to_be_used].notna()]
        tag_used_gdf = gdf_non_residential[tag_to_be_used].copy()
        tag_used_gdf = [f"{tag_to_be_used}:{t}" for t in tag_used_gdf]
        gdf_non_residential = gdf_non_residential[['geometry']]
        gdf_non_residential['type'] = 'NON_RES'
        gdf_non_residential['aux info'] = 'non_residential_aux_tag'
        gdf_non_residential['tag used'] = tag_used_gdf
        gdf_out_list.append(gdf_non_residential.copy())
        gdf = gdf.drop(gdf_non_residential.index)

    # Consider the unknown as residential
    gdf = gdf[['geometry']]
    gdf['type'] = 'RES'
    gdf['aux info'] = 'residential_unknown_tag'
    gdf['tag used'] = None
    gdf_out_list.append(gdf)
    gdf_out = pd.concat(gdf_out_list, axis=0)

    return gdf_out


def building_types_separate_joint(buildings):
    buildings_out = []
    for building in buildings:
        buildings_out += re.split(";", building)
    return buildings_out


def _segment_polygon(polygon, num_segments_per_line):
    """
    Segment a polygon.

    Parameters:
    - polygon (shapely.geometry.Polygon): The polygon to segment.
    - num_segments_per_line (int): Sqrt of the number of segments to divide the polygon into.

    Returns:
    - list of shapely.geometry.Polygon: List of segmented polygons.
    """
    xmin, ymin, xmax, ymax = polygon.bounds
    segment_width = (xmax - xmin) / num_segments_per_line
    segment_height = (ymax - ymin) / num_segments_per_line
    segments = []
    for i in range(num_segments_per_line):
        for j in range(num_segments_per_line):
            x_start = xmin + i * segment_width
            y_start = ymin + j * segment_height
            x_end = x_start + segment_width
            y_end = y_start + segment_height
            segment = Polygon([(x_start, y_start), (x_end, y_start), (x_end, y_end), (x_start, y_end)])
            if segment.intersects(polygon):
                segments.append(segment.intersection(polygon))
    return segments


def _combine_buildings_features(gdf_raw):
    if 'building' in gdf_raw:
        footprints = gdf_raw[pd.notna(gdf_raw['building'])] #Only buildings
        not_buildings = gdf_raw[pd.notna(gdf_raw['building']) == False]
    else:
        footprints = gpd.GeoDataFrame(columns=gdf_raw.columns)
        not_buildings = gdf_raw

    not_used_objects_dict = {"osmid": [],
                             "element_type": [],
                             "geometry": [],
                             "tag": [],
                            }

    footprint_id2features = dict()

    # Read the features that are in the footprint df
    tags_selected = [tag.lower() for tag in tags.keys() if tag != 'building' and tag != 'surface'] # ''surface' is downloaded just to avoid errors downloading data on regions with a few buildings'

    for tag in tags_selected:
        if tag in footprints:
            tags_df = footprints[tag].loc[pd.notna(footprints[tag])]
            for index in tags_df.index:
                osmid = index[1]
                building_types = re.split(";",tags_df[index])
                for building_type in building_types:
                    if osmid not in footprint_id2features:
                        footprint_id2features[osmid] = [f"{tag}:{building_type}"]
                    else:
                        footprint_id2features[osmid].append(f"{tag}:{building_type}")

    if footprints.shape[0] > 0:
        footprint_out = _define_type(footprints)
    else:
        footprint_out = gpd.GeoDataFrame(columns=['el_type', 'osmid', 'geometry', 'type', 'aux info', 'tag used'])

    # Read the features from the auxiliary data to store the features in the dictionary
    for tag in tags_selected:
        if tag in not_buildings:
            tags_df = not_buildings[[tag,'geometry']].loc[pd.notna(not_buildings[tag])]
            #Test if overlaps
            for i in range(tags_df.shape[0]):
                non_bulding_polygon = tags_df.iloc[i].geometry
                building_info = tags_df[tag].iloc[i]
                added = False
                for index in footprints.loc[footprints.intersects(non_bulding_polygon)].index: #the intersecting ones
                    osmid = index[1]
                    building_infos = [f"{tag}:{info}" for info in re.split(";", building_info)]
                    for info in building_infos:
                        if osmid not in footprint_id2features:
                            footprint_id2features[osmid] = [info]
                        else:
                            footprint_id2features[osmid].append(info)
                    added = True

                if added == False: #Not overlapping
                    osmid_not_building = tags_df.index[i][1]
                    element_type_not_building = tags_df.index[i][0]
                    building_infos = [f"{tag}:{info}" for info in re.split(";", building_info)]
                    for info in building_infos:
                        not_used_objects_dict["osmid"].append(osmid_not_building)
                        not_used_objects_dict["element_type"].append(element_type_not_building)
                        not_used_objects_dict["geometry"].append(non_bulding_polygon)
                        not_used_objects_dict["tag"].append(info)

    not_used_objects_gdf = gpd.GeoDataFrame.from_dict(not_used_objects_dict)
    return footprint_out, footprint_id2features, not_used_objects_gdf


def _merge_dictionaries_of_lists(dict_1, dict_2):
    dict_out = dict_1.copy()
    for key in dict_2.keys():
        if key in dict_out:
            dict_out[key] += dict_2[key]
        else:
            dict_out[key] = dict_2[key]
    return dict_out


# Change the name of this function
def use_auxiliary_data(gdf, footprint_id2features):
    """
    Enhance the GeoDataFrame by updating auxiliary data based on OSM.

    It iterates over the GeoDataFrame (`gdf`) and updates the 'aux info', 'type', and 'tag used' 
    columns based on the OpenStreetMap (OSM) features associated with each footprint ID. 
    It identifies and categorizes segments as either 'residential' or 'non-residential' based on 
    auxiliary data and tags from `footprint_id2features`.

    Parameters:
    - gdf (geopandas.GeoDataFrame): GeoDataFrame containing segments to be enhanced with auxiliary information.
    - footprint_id2features (dict): Dictionary mapping OSM footprint IDs to their corresponding feature tags.

    Returns:
    - geopandas.GeoDataFrame: The input GeoDataFrame, with updated 'aux info', 'type', and 'tag used' columns where applicable.
    """
    indices = gdf.index
    for i in tqdm(range(gdf.shape[0])):
        index = indices[i]
        osmid = index[1]
        if osmid in footprint_id2features and (gdf.loc[[index],'aux info'] == 'residential_unknown_tag').all():
            for complete_tag in footprint_id2features[osmid]:
                tag_split = re.split(':', complete_tag)
                tag = tag_split[0]
                specification = tag_split[1]

                shall_skip = False
                if tag in col2skip_type.keys(): 
                    if specification in col2skip_type[tag]:
                        shall_skip = True

                if specification not in tags_do_not_consider and not shall_skip:
                    if tag in col2residential_type and specification.lower() in col2residential_type[tag]:
                        gdf.loc[[index],'aux info'] = 'residential_auxiliary'
                        gdf.loc[[index],'type'] = 'RES'
                        gdf.loc[[index],'tag used'] = f"{tag}:{specification.lower()}"
                    elif tag in col2non_residential_type and specification.lower() in col2non_residential_type[tag]:
                        gdf.loc[[index],'aux info'] = 'non_residential_auxiliary'
                        gdf.loc[[index],'type'] = 'NON_RES'
                        gdf.loc[[index],'tag used'] = f"{tag}:{specification.lower()}"
                    elif tag in to_non_residential:
                        gdf.loc[[index],'aux info'] = 'non_residential_auxiliary_generic_tag'
                        gdf.loc[[index],'type'] = 'NON_RES'
                        gdf.loc[[index],'tag used'] = f"{tag}:{specification.lower()}"
    return gdf


def generate_gdf_with_segments(polygon, num_segments, tags):
    """
    Generate a GeoDataFrame from a polygon by segmenting it into smaller parts and retrieving OSM attributes.

    It attempts to segment the input polygon into a specified number of segments. 
    If an error occurs, it retries with fewer segments until successful or until only one segment remains.

    Parameters:
    - polygon (shapely.geometry.Polygon): The polygon to be segmented.
    - num_segments (int): The initial number of segments to divide the polygon into.
    - tags (dict): Dictionary of OSM tags to query for each segment.

    Returns:
    - geopandas.GeoDataFrame: GeoDataFrame containing all segments with their OSM attributes.
    - dict: A dictionary mapping footprint IDs to features.
    - geopandas.GeoDataFrame: GeoDataFrame containing any segments that were not used.
    """
    done = False
    while num_segments > 1 and not done:
        try:
            segments = _segment_polygon(polygon, num_segments)
            gdf, footprint_id2features, gdf_not_used = generate_gdf_from_segments(segments, tags)
            done = True
            print("Done!")
        except:
            num_segments -= 1
            print(f"Trial run with fewer segments (num. segments:{num_segments}).")
    
    if num_segments == 1: #to get a possible error
        segments = _segment_polygon(polygon, num_segments)
        gdf, footprint_id2features, gdf_not_used = generate_gdf_from_segments(segments, tags)

    return gdf, footprint_id2features, gdf_not_used


def generate_gdf_from_segments(segments, tags):
    """
    Generate a GeoDataFrame from segments using OSMnx's features_from_polygon function.

    Parameters:
    - segments (list of shapely.geometry.Polygon): List of segmented polygons.
    - tags (dict): Dictionary of OSM tags to query.

    Returns:
    - geopandas.GeoDataFrame: GeoDataFrame containing all the segments with their OSM attributes.
    """
    gdf_list = []
    not_used_objects_list = []
    footprint_id2features = dict()
    for segment in tqdm(segments):
        gdf_raw = ox.features_from_polygon(segment, tags)
        gdf, footprint_id2features_partial, not_used_objects_df = _combine_buildings_features(gdf_raw)
        footprint_id2features = _merge_dictionaries_of_lists(footprint_id2features, footprint_id2features_partial)
        not_used_objects_list.append(not_used_objects_df)
        if gdf.shape[0] > 0:
            gdf_list.append(gdf)

    df = pd.concat(gdf_list)
    gdf_not_used = gpd.GeoDataFrame(pd.concat(not_used_objects_list).drop_duplicates())
    columns = list(df.columns)#before adding the numbers
    df['line_number'] = list(range(df.shape[0]))
    indices_df = df.astype(str).drop_duplicates(subset=columns)
    indices = indices_df['line_number']
    df.drop(columns=['line_number'], inplace=True)
    gdf = gpd.GeoDataFrame(df.iloc[indices])
    gdf = gdf.set_crs(gdf_raw.crs)
    gdf_not_used = gdf_not_used.set_crs(gdf_raw.crs)

    return gdf, footprint_id2features, gdf_not_used
