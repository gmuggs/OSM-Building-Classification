# Extracting the U.S. building types from OpenStreetMap data

Codes to reproduce the paper "Extracting the U.S. building types from OpenStreetMap data."

## Data

Download the input data sets as follows before running the codes. 

Ground truth data list:

- [Minneapolis and St. Paul](https://gisdata.mn.gov/dataset/us-mn-state-metc-plan-generl-lnduse2020) (```Metropolitan_reg_Minneapolis_and_St_Paul/GeneralizedLandUse2020.shp```);
- [Baltimore, MD](https://opendata.baltimorecountymd.gov/datasets/e45bd5ad0de14bf988f825dd7a4431af_0/explore?location=39.452147%2C-76.611050%2C10.00) (```baltimore/Landuse.shp```);
- [Boulder, CO](https://osf.io/3j46v/) (```Boulder_admin_buildings/Boulder_admin_buildings.shp```);
- [Fairfax, VA (city)](https://data-cityoffairfax.opendata.arcgis.com/) (```Land_Use_Existing_-2984936049164631990/Land_Use_Existing.shp```);
- [Fairfax, VA (county)](https://www.fairfaxcounty.gov/maps/open-geospatial-data) (```Existing_Land_Use_-_Generalized/Existing_Land_Use_-_Generalized.shp```);
- [Hanover, VA](https://parcelmap.hanovercounty.gov/#) (```Hanover_Parcels_-1335205000025218776/Hanover_Parcels.shp```);
- [Mecklenburg, NC](https://maps.mecknc.gov/openmapping/data.html) (```Mecklenburg_admin_buildings_new/Parcel_Landuse.shp```).

Other datasets:

- [CBSA-EST2023-ALLDATA](https://www.census.gov/data/tables/time-series/demo/popest/2020s-total-metro-and-micro-statistical-areas.html) (```cbsa-est2023-alldata.csv```);
- [Counties 1:500,000 (national)](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.2023.html#list-tab-1883739534) (```cb_2023_us_county_500k/cb_2023_us_county_500k.shp```).

All of these files must be placed in the ```raw_data``` folder.


## Validation

To perform the validation, first run the ```cretate_ground_truth.py``` script to generate the ground truth dataset. Then run the ```validate.py``` script. 

```bash
python cretate_ground_truth.py
...
python validate.py
```

## Generating the dataset 
To generate the database, use the ``classification_USA.py`` script.

```bash
python classification_USA.py
```

This script can take a long time to run; the already processed dataset can be found in the [OSM-Building-Classification](https://osf.io/utgae/) repository. 

## Citation Request

If you publish a scientific paper that uses this material, please cite the following:

Arruda HF, Reia SM, Ruan S,  Atwal KS, Kavak H, Anderson T, Pfoser D. Extracting the U.S. building types from OpenStreetMap data. arXiv preprint [arXiv:2409.05692](https://arxiv.org/pdf/2409.05692). 2024.
