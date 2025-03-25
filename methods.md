# Exploration of land-cover changes in the Protected Areas and buffer zones of Goa's wildlife sanctuaries and national parks

This exploration was done in Python using the following packages and libraries:

- geopandas
- matplotlib
- pandas
- ee
- geemap

I used the interactive shell IPython as it allows for a richer visual experience and provides methods for previewing maps and graphs.

Data is drawn from:

- _Who made the PA polygons?_
- [The SHRUG](https://www.devdatalab.org/shrug)
- [Global 30-meter Land Cover Change Dataset (1985-2022) - (GLC_FCS30D)](https://gee-community-catalog.org/projects/glc_fcs/)

## Data preparation methods

### 1 - Protected area, buffer & village/town polygons

#### 1.1 - Protected area & buffer polygons

In order to capture meaningful land cover changes we first need to create useful polygons to define areas of interest. I started with the shapefile "Notified_PA_Goa" created by \_\_\_\_ for each of the 7 notified protected areas:

1. Mhadei Wildlife Sanctuary
2. Bhagwan Mahavir Wildlife Sanctuary (N)\*
3. Mollem National Park
4. Bhagwan Mahavir Wildlife Sanctuary (S)\*
5. Bondla Wildlife Sacntuary
6. Netravali Wildlife Sanctuary
7. Cotigaon Wildlife Sanctuary
8. Dr. Salim Ali Wildlife Sanctuary

\* as per the shapefile Bhagwan Mahavir Wildlife Sanctuary is made up of 2 non-contiguous polygons. They will be treated independently for this analysis.

```
import geopandas as gp

pas = gp.read_file('data/Goa_protected_areas/Notified_PA_Goa.shp')

pas = pas.drop(columns=['Shape_Leng', 'Shape_Area'])
```

In order to consistently reference a single polygon the "Name" column of the dataset needs to be unique.

```
pas = pas.rename(columns={'Name': 'name'})

# Use index values to make ESZ names unique
pas = pas.reset_index()

pas['index'] = pas['index'].astype(str)

pas['name'] = pas['index'] + '_' + pas['name'].str.replace(' ', '_').str.replace('.', '')

# Drop old index column
pas = pas.drop(columns=['index'])
```

Since all the areas of interest lie within the state of Goa, I have chosen to use the coordinate reference system [EPSG:7779](https://spatialreference.org/ref/epsg/7779/).

The "geometry" column represents the boundaries of the PAs not including the 1,000 m buffers. Therefore, the buffers would be the set of polygons extending from the current geometry columns outward 1,000 m. The polygons include a Z axis which is not relevant for the current analysis.

```
pas = pas.rename(columns={'geometry': 'pa'})

pas['pa'] = pas['pa'].force_2d()

# Set primary geometry
pas = pas.set_geometry('pa')

# Reproject to correct CRS
pas = pas.to_crs('EPSG:7779')

# Create polygons 1,000m larger in all directions
pas['buffer'] = pas['pa'].buffer(1000)

# Subtract PA from the new buffer polygon
pas['buffer'] = pas['buffer'].difference(pas['pa'])
```

The buffers constructed above do not take into account the fact that most of the PAs are contiguous and along Goa's eastern border. The buffers overlap each other, other PAs or fall outside the state. They need to be clipped to account for these inconsistencies.

The state's boundaries are taken from [the SHRUG](https://www.devdatalab.org/shrug) and preprocessed to include only the polygon representing Goa and have been reprojected into [EPSG:7779](https://spatialreference.org/ref/epsg/7779/).

This data set is saved as "eszs.feather".

```
state = gp.read_feather('feathers/admin_units/state.feather')

# Keep only parts of the buffers inside the state
pas['buffer'] = pas['buffer'].intersection(state.loc['30', 'geometry'])

pa_polygon_list = pas['pa'].to_list()

# Subtract PAs from all buffers
# Keep only buffer areas outside PAs
for pa_polygon in pa_polygon_list:
     pas['buffer'] = pas['buffer'].difference(pa_polygon)

# Uncomment below to save the dataset
# pas.to_feather('feathers/eszs.feather')
```

**ISSUE** The buffers also intersect with themselves. For any analysis done on a per-PA basis this will not have an impact. However, any analysis done on a state-wide basis will include some double counting for the area within the intersection of the buffers.

### 1.2 - Village/town polygons

Village/town polygons are taken from [the SHRUG](https://www.devdatalab.org/shrug). The dataset consists of the subset of villages/towns that intersect with either a PA or a buffer. The dataset has already been reprojected to [EPSG:7779](https://spatialreference.org/ref/epsg/7779/).

From here on lets refer to them as admin. units.

**ISSUE** I have no idea what the "mdds_og" column in the SHRUG town/village shapefiles is for.

Each admin. unit needs to be linked to a specific PA or buffer and, its area clipped to only the part that overlaps with that PA or buffer. Some admin. units appear in the final dataset multiple times because they intersect with multiple PAs and/or buffers.

The dataset is indexed at the following levels:

1. ESZ name - e.g. 0_Mhadei_WLS
2. ESZ part - either "pa" or "buffer"
3. Political Census of India 2011 state ID
4. Political Census of India 2011 district ID
5. Political Census of India 2011 subdistrict ID
6. Political Census of India 2011 town/village ID

The dataset is saved as "clipped_villages.feather".

```
import pandas as pd

villages = gp.read_feather('feathers/admin_units/villages.feather')

def clip_villages(row):
# Create apply function
# For each PA & buffer,
#   clip admin. units that intersect,
#   drop admin. units that do not intersect,
#   add a column showing whether the admin. unit
#   intersects with a PA or a buffer and
#   add another column showing which one.
# Reindex and add to list.

    pa_gdf = villages.copy()
    pa_gdf['geometry'] = pa_gdf['geometry'].intersection(row['pa'])
    pa_gdf = pa_gdf[~(pa_gdf['geometry'].is_empty | pa_gdf['geometry'].isna())]
    buffer_gdf = villages.copy()
    buffer_gdf['geometry'] = buffer_gdf['geometry'].intersection(row['buffer'])
    buffer_gdf = buffer_gdf[~(buffer_gdf['geometry'].is_empty | buffer_gdf['geometry'].isna())]
    gdf = pd.concat([pa_gdf, buffer_gdf], keys=['pa', 'buffer'], names=['part'])
    gdf['esz'] = row['name']
    gdf = gdf.reset_index()
    gdf = gdf.set_index(['esz', 'part', 'pc11_state_id', 'pc11_district_id', 'pc11_subdistrict_id', 'pc11_town_village_id'])
    gdfs.append(gdf)

gdfs = []

pas.apply(clip_villages, axis=1)

# Concatenate all the GeoDataFrames together
clipped_villages = pd.concat(gdfs)

# Uncomment below to save the dataset
# clipped_villages.to_feather('feathers/clipped_villages.feather')
```

#### 1.3 - Maps

Mapping the clipped villages over their respective PAs and buffers gives the following figures.

Maps are saved in the "pngs" folder.

```
import matplotlib.pyplot as plt

# Create the figure and axis
fig, ax = plt.subplots(layout='tight', num='State-wide')

# Remove axis markers
plt.axis('off')

# Plot state
state.plot(ax=ax, linewidth=0.5, ec='grey', fc='none', linestyle='--')

# Add state name
ax.annotate(text='Goa', xy=state.loc['30'].geometry.representative_point().coords[0], ha='center', wrap=True, color='grey', fontsize='medium')

# Plot all admin. unit polygons
clipped_villages.plot(ax=ax, linewidth=0.5, ec='grey', fc='none', linestyle='--')

# Plot all PAs
pas['pa'].plot(ax=ax, fc='none', ec='green', linewidth=0.5)

# Plot all buffers
pas['buffer'].plot(ax=ax, fc='none', ec='blue', linewidth=0.5)

# Add PA names with apply function
def add_names(row):
    text = ' '.join(row['name'].split('_')[1:])
    pa = gp.GeoSeries(row.pa)
    rep_point = pa.representative_point().get_coordinates().values[0]
    ax.annotate(
        text=text,
        xy=(rep_point[0], rep_point[1]),
        ha='center',
        wrap=True,
        color='green',
        fontsize='medium',
    )

pas.apply(add_names, axis=1)

# Uncomment below to save the state-wide png
# fig.savefig('pngs/state_wide_pas_buffers.png', dpi=150, format='png', bbox_inches='tight')

# Add admin. unit names with apply function
def village_names(row, ax):
     rep_point = gp.GeoSeries(row.geometry).representative_point().get_coordinates().values[0]
     ax.annotate(
         text=row['name'],
         xy=(rep_point[0], rep_point[1]),
         ha='center',
         wrap=True,
         color='grey',
         fontsize='small',
     )

def map_pas(row):
# Create apply function
# For each PA,
#   create a figure and axis,
#   plot intersecting admin. units,
#   plot PA,
#   add admin. unit names,
#   add PA name
# Add to list

     map_name = row['name'] + '_PA'
     text = ' '.join(row['name'].split('_')[1:]) + ' PA'
     pa = gp.GeoSeries(row['pa'])
     fig, ax = plt.subplots(layout="tight", num=map_name)
     plt.axis("off")
     v = clipped_villages.loc[(row['name'], 'pa')]
     v.plot(ax=ax, fc='none', ec='grey', linestyle='--', linewidth=0.5)
     pa.plot(ax=ax, fc='none', ec='green', linewidth=0.5)
     v.apply(village_names, axis=1, args=(ax,))
     rep_point = pa.representative_point().get_coordinates().values[0]
     ax.annotate(
         text=text,
         xy=(rep_point[0], rep_point[1]),
         ha='center',
         wrap=True,
         color='green',
         fontsize='medium',
     )
     figs.append(fig)

def map_buffers(row):
# Create apply function
# For each buffer,
#   create a figure and axis,
#   plot intersecting admin. units,
#   plot buffer,
#   add admin. unit names,
#   add PA name
# Add to list

     map_name = row['name'] + '_buffer'
     text = ' '.join(row['name'].split('_')[1:]) + ' buffer'
     pa = gp.GeoSeries(row['pa'])
     buffer = gp.GeoSeries(row['buffer'])
     fig, ax = plt.subplots(layout="tight", num=map_name)
     plt.axis("off")
     v = clipped_villages.loc[(row['name'], 'buffer')]
     v.plot(ax=ax, fc='none', ec='grey', linestyle='--', linewidth=0.5)
     buffer.plot(ax=ax, fc='none', ec='blue', linewidth=0.5)
     v.apply(village_names, axis=1, args=(ax,))
     rep_point = pa.representative_point().get_coordinates().values[0]
     ax.annotate(
         text=text,
         xy=(rep_point[0], rep_point[1]),
         ha='center',
         wrap=True,
         color='blue',
         fontsize='medium',
     )
     figs.append(fig)

figs = []

pas.apply(map_pas, axis=1)

pas.apply(map_buffers, axis=1)

# Uncomment below to save all individual PA and buffer maps
# for fig in figs:
    fig.savefig('pngs/' + fig.get_label() + '.png', dpi=150, format='png', bbox_inches='tight')
```

![State-wide PAs & buffers](pngs/state_wide_pas_buffers.png)
![Mhadei WLS PA](pngs/0_Mhadei_WLS_PA.png)
![Mhadei WLS buffer](pngs/0_Mhadei_WLS_buffer.png)
![Bhagwan Mahavir (N) WLS PA](pngs/1_Bhagwan_Mahavir_WLS_PA.png)
![Bhagwan Mahavir (N) WLS buffer](pngs/1_Bhagwan_Mahavir_WLS_buffer.png)
![Mollem NP PA](pngs/2_Mollem_NP_PA.png)
![Mollem NP buffer](pngs/2_Mollem_NP_buffer.png)
![Bhagwan Mahavir (S) WLS PA](pngs/3_Bhagwan_Mahavir_WLS_PA.png)
![Bhagwan Mahavir (S) WLS buffer](pngs/3_Bhagwan_Mahavir_WLS_buffer.png)
![Bondla WLS PA](pngs/4_Bondla_WLS_PA.png)
![Bondla WLS buffer](pngs/4_Bondla_WLS_buffer.png)
![Netravali WLS PA](pngs/5_Netravali_WLS_PA.png)
![Netravali WLS buffer](pngs/5_Netravali_WLS_buffer.png)
![Cotigaon WLS PA](pngs/6_Cotigaon_WLS_PA.png)
![Cotigaon WLS buffer](pngs/6_Cotigaon_WLS_buffer.png)
![Dr Salim Ali WLS PA](pngs/7_Dr_Salim_Ali_WLS_PA.png)
![Dr Salim Ali WLS buffer](pngs/7_Dr_Salim_Ali_WLS_buffer.png)

### 2 - Land-cover data

Land-cover data is drawn from the [Global 30-meter Land Cover Change Dataset (1985-2022) - (GLC_FCS30D)](https://gee-community-catalog.org/projects/glc_fcs/). More information on it and the land-cover types used can be found in the paper [GLC_FCS30D: the first global 30 m land-cover dynamics monitoring product with a fine classification system for the period from 1985 to 2022 generated using dense-time-series Landsat imagery and the continuous change-detection method](https://essd.copernicus.org/articles/16/1353/2024/).

The dataset is divided into 2 sections: the annual section containing annual data from 2000 to 2022, and the five-yearly section with five-yearly data from 1985 to 1995.

The sections are Google Earth Engine image collections containing 2 images each, divided geographically. Each band in each section represents an annual/five-yearly dataset. Therefore, the five-yearly set has 3 bands and the annual has 23. Each pixel represents a 30x30 m area and is coded with 1 of the land-cover types as described in the paper above.

The land-cover types, their IDs, descriptive names and colour codes are stored in the "GLC_FCS30D_land_cover_types.feather" dataset.

The final dataset is created by taking the frequency of each land-cover type within each admin. unit polygon for each time interval and multiplying it by the resolution (30x30 m). This results in a dataframe with each admin. unit from "clipped_villages.feather" associated with the area in square metres of each land-cover type for each time interval (either five-yearly or annual).

Each admin. unit is indexed by:

1. ESZ name - e.g. 0_Mhadei_WLS
2. ESZ part - either "pa" or "buffer"
3. Political Census of India 2011 state ID
4. Political Census of India 2011 district ID
5. Political Census of India 2011 subdistrict ID
6. Political Census of India 2011 town/village ID
7. Year - 1985 to 2000 in 5 year intervals, 2000 to 2022 in 1 year intervals
8. Name of the admin. unit

The admin. units can be linked back to their individual polygons and the polygons for the PAs and buffers using the "clipped_villages.feather" dataset.

Land-cover types are indexed by:

1. Basic ID
2. Level-1 ID
3. Fine ID

These IDs can be linked back to descriptive names using the "GLC_FCS30D_land_cover_types.feather" dataset.

```
import ee

import geemap as gm

# Uncomment to authenticate with your
#   Google Earth Engine credentials
# ee.Authenticate()

# Initialise with your own Google Cloud project
ee.Initialize(project='XXXXXXXXXXXXXX')

# Convert GeoDataFrame to Earth Engine FeatureCollection
#   Reporject to EPSG:4326, Google Earth Engine's default
to_fc = clipped_villages.drop(columns=['mdds_og'])

to_fc = to_fc.to_crs('EPSG:4326')

village_fc = gm.gdf_to_ee(to_fc)

# Access GLC_FCS30D 2000 - 2022 annual dataset and
#   filter for area of interest
glc_annual = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/annual').filterBounds(village_fc)

# Access GLC_FCS30D 1985 - 1995 five-yearly dataset and
#   filter for area of interest
glc_five_year = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/five-years-map').filterBounds(village_fc)

# Mosaic the 2 images together for each ImageCollection
glc_annual = glc_annual.mosaic()

glc_five_year = glc_five_year.mosaic()

# Rename bands to years
glc_annual = glc_annual.rename(ee.List.sequence(2000, 2022).map(lambda x: ee.Number(x).format('%04d')))

glc_five_year = glc_five_year.rename(ee.List.sequence(1985, 1995, 5).map(lambda x: ee.Number(x).format('%04d')))

# Combine all bands into 1 image
glc_all_years = glc_five_year.addBands(glc_annual)

# Get frequency for
#   each land-cover type,
#   for each admin. unit,
#   for each year
lc_data_fc = glc_all_years.reduceRegions(
    collection=village_fc,
    reducer=ee.Reducer.frequencyHistogram(),
    scale=30,
    crs='EPSG:7779')

# Drop all geometries
lc_data_fc = lc_data_fc.select(propertySelectors=['.*'], retainGeometry=False)

# Convert FeatureCollection to DataFrame
lc_data_df = gm.ee_to_df(lc_data_fc)

# Unpivot years from columns to values
lc_data_df = pd.melt(lc_data_df, id_vars=['esz', 'part', 'pc11_state_id', 'pc11_district_id', 'pc11_subdistrict_id', 'pc11_town_village_id', 'name'], var_name='year')

# Spread "value" column dictionary into
#   columns of land-cover types
lc_data_df = pd.concat([lc_data_df, pd.json_normalize(lc_data_df['value'])], axis=1)

# Convert "year" column to datetime
lc_data_df['year'] = pd.to_datetime(lc_data_df['year'], format="%Y")

# Set index
lc_data_df = lc_data_df.set_index(['esz', 'part', 'pc11_state_id', 'pc11_district_id', 'pc11_subdistrict_id', 'pc11_town_village_id', 'name', 'year'])

# Sort land-cover type columns
lc_type_cols = lc_data_df.select_dtypes(include='number').columns.to_list()

lc_type_cols = [int(x) for x in lc_type_cols if x != '0']

lc_type_cols.sort()

lc_type_cols = [str(x) for x in lc_type_cols]

lc_type_cols = lc_type_cols + ['0']

lc_data_df = lc_data_df[lc_type_cols]

# Index columns by land-cover type aggregations
lc_types = pd.read_feather('feathers/GLC_FCS30D_landcover_types.feather')

lc_types = lc_types.reset_index()

lc_type_tuples = list(lc_types[['basic_id', 'level_1_id', 'fine_id']].itertuples(index=False, name=None))

lc_type_tuples = [x for x in lc_type_tuples if str(x[2]) in lc_type_cols]

lc_type_tuples = lc_type_tuples + [('XXX', 'XXX', 0)]

lc_data_df.columns = pd.MultiIndex.from_tuples(t for t in lc_type_tuples if str(t[2]) in lc_type_cols)

lc_data_df.columns.names = ['basic_id', 'level_1_id', 'fine_id']

# Replace NaNs with 0s
lc_data_df.fillna(0)

# Uncomment below to save frequency dataset
# lc_data_df.to_feather('feathers/land_cover_frequency.feather')

# Multiply all columns by 30*30 to convert frequency to area
lc_data_df *= (30 * 30)

# Uncomment below to save area dataset
# lc_data_df.to_feather('feathers/land_cover_area.feather')

# Check the difference between total area of
#   an admin. unit's total land-cover types and
#   polygon
areas = pd.DataFrame(lc_data_df.sum(axis=1))

areas = areas.rename(columns={0: 'land_cover'})

areas['polygon'] = clipped_villages['geometry'].area

areas['difference'] = areas['polygon'] - areas['land_cover']

area_stats = areas[['polygon', 'difference']].describe()

print(area_stats.to_markdown())

# Uncomment below to save the area dataset
# areas.to_feather('feathers/areas.feather')
```

##### Difference in areas between land-cover and polygons

|      |   polygon(m2) | difference (m2) |
| :--- | ------------: | --------------: |
| mean |  4,159,400.00 |          362.42 |
| std  |  8,793,100.00 |          421.17 |
| min  |          1.05 |         -723.20 |
| 25%  |    201,948.00 |          107.82 |
| 50%  |  1,565,900.00 |          256.96 |
| 75%  |  3,697,260.00 |          502.43 |
| max  | 85,424,800.00 |        2,897.57 |

As the table above shows there is a difference between the area of any given admin. unit when calculated by summing up all the land-cover type areas vs. the area of its polygon. This is because when the global land-cover dataset is reduced to match the polygons defining the admin. units, some pixels are only partially contained within the polygons. The [frequency histogram reducer](https://developers.google.com/earth-engine/apidocs/ee-reducer-frequencyhistogram) uses a weighting algorithm to determine if the value of that pixel should be included or not.

On average this difference represents less than 0.001% of the area of the admin. unit, granted with a significant variability in the statistic.

## Data analysis methods

### 1 - Grouping and aggregating data

Certain land-cover types cover a significantly greater proportion of both the PAs and buffers. Average fractional values over the entire dataset aggregated to the basic classification system show which types predominate in each PA and buffer.

```
import pandas as pd

# Read in data
land_cover_area = pd.read_feather('feathers/land_cover_area.feather')

lc_types = pd.read_feather('feathers/GLC_FCS30D_landcover_types.feather')

areas = pd.read_feather('feathers/areas.feather')

# Sum all admin. units grouped by ESZ PA and buffer
land_cover_area = land_cover_area.groupby(['esz', 'part', 'year']).sum()

areas = areas.groupby(['esz', 'part', 'year']).sum()

# Convert area to fraction of total
land_cover_fraction = land_cover_area.div(areas['land_cover'], axis=0)

# Average all years' land-cover fractions grouped by ESZ PA and buffer
# Transpose
fine_mean = land_cover_fraction.groupby(['esz', 'part']).mean().T

# Reset index to names of land-cover types
fine_mean[['basic_name', 'level_1_name', 'fine_name']] = lc_types[['basic_classification_system', 'level_1_validation_system', 'fine_classification_system']]

fine_mean.loc[('XXX', 'XXX', 0), ['basic_name', 'level_1_name', 'fine_name']] = 'Filled value'

fine_mean = fine_mean.set_index(['basic_name', 'level_1_name', 'fine_name'])

# Aggregate means by land-cover aggregation levels
level_1_mean = fine_mean.groupby(['basic_name', 'level_1_name']).sum()

basic_mean = fine_mean.groupby(['basic_name']).sum()

eszs = list(set(x[0] for x in fine_mean.columns.to_list()))

eszs.sort()

# Print Markdown tables of basic classification types for each ESZ
for e in eszs:
     print()
     print(e.replace('_', ' '))
     print()
     print(basic_mean[e].round(4).to_markdown())

# Uncomment below to save mean datasets
# fine_mean.to_feather('feathers/fine_mean.feather')
# level_1_mean.to_feather('feathers/level_1_mean.feather')
# basic_mean.to_feather('feathers/basic_mean.feather')
```

##### 0 Mhadei WLS

| basic_name         | buffer |     pa |
| :----------------- | -----: | -----: |
| Bare areas         | 0.0002 | 0.0001 |
| Cropland           | 0.0085 | 0.0025 |
| Filled value       |      0 |      0 |
| Forest             | 0.9672 | 0.9952 |
| Grassland          | 0.0008 | 0.0002 |
| Impervious surface | 0.0012 | 0.0002 |
| Shrubland          | 0.0004 | 0.0008 |
| Water body         | 0.0134 | 0.0002 |
| Wetland            | 0.0083 | 0.0008 |

##### 1 Bhagwan Mahavir WLS

| basic_name         | buffer |     pa |
| :----------------- | -----: | -----: |
| Bare areas         |      0 |      0 |
| Cropland           | 0.0101 | 0.0011 |
| Filled value       |      0 |      0 |
| Forest             | 0.9805 | 0.9984 |
| Grassland          | 0.0067 | 0.0002 |
| Impervious surface | 0.0009 |      0 |
| Shrubland          |  0.001 | 0.0003 |
| Water body         | 0.0001 |      0 |
| Wetland            | 0.0007 |      0 |

##### 2 Mollem NP

| basic_name         | buffer |     pa |
| :----------------- | -----: | -----: |
| Bare areas         | 0.0002 |      0 |
| Cropland           | 0.0106 | 0.0012 |
| Filled value       |      0 |      0 |
| Forest             | 0.9739 | 0.9979 |
| Grassland          | 0.0041 | 0.0007 |
| Impervious surface | 0.0088 |      0 |
| Shrubland          | 0.0005 | 0.0002 |
| Water body         | 0.0005 |      0 |
| Wetland            | 0.0014 |      0 |

##### 3 Bhagwan Mahavir WLS

| basic_name         | buffer |     pa |
| :----------------- | -----: | -----: |
| Bare areas         | 0.0004 |      0 |
| Cropland           | 0.0185 |  0.002 |
| Filled value       |      0 |      0 |
| Forest             | 0.9599 | 0.9963 |
| Grassland          | 0.0096 | 0.0013 |
| Impervious surface | 0.0019 | 0.0002 |
| Shrubland          | 0.0019 | 0.0002 |
| Water body         |  0.004 |      0 |
| Wetland            | 0.0037 | 0.0001 |

##### 4 Bondla WLS

| basic_name         | buffer |     pa |
| :----------------- | -----: | -----: |
| Bare areas         |      0 |      0 |
| Cropland           | 0.0014 | 0.0001 |
| Filled value       |      0 |      0 |
| Forest             | 0.9965 | 0.9997 |
| Grassland          | 0.0001 |      0 |
| Impervious surface |  0.002 |      0 |
| Shrubland          | 0.0001 |      0 |
| Water body         |      0 |      0 |
| Wetland            |      0 | 0.0001 |

##### 5 Netravali WLS

| basic_name         | buffer |     pa |
| :----------------- | -----: | -----: |
| Bare areas         | 0.0004 |      0 |
| Cropland           | 0.0141 | 0.0016 |
| Filled value       | 0.0002 | 0.0001 |
| Forest             | 0.8129 | 0.9803 |
| Grassland          | 0.0061 | 0.0011 |
| Impervious surface | 0.0003 |      0 |
| Shrubland          | 0.0114 |  0.015 |
| Water body         | 0.1094 | 0.0005 |
| Wetland            | 0.0452 | 0.0013 |

##### 6 Cotigaon WLS

| basic_name         | buffer |     pa |
| :----------------- | -----: | -----: |
| Bare areas         |      0 |      0 |
| Cropland           | 0.0539 | 0.0054 |
| Filled value       |  0.001 | 0.0014 |
| Forest             |  0.926 | 0.9766 |
| Grassland          | 0.0016 |      0 |
| Impervious surface | 0.0005 |      0 |
| Shrubland          | 0.0169 | 0.0165 |
| Water body         |      0 |      0 |
| Wetland            |      0 |      0 |

##### 7 Dr Salim Ali WLS

| basic_name         | buffer |     pa |
| :----------------- | -----: | -----: |
| Bare areas         | 0.0013 | 0.0007 |
| Cropland           | 0.0875 | 0.0042 |
| Filled value       |      0 |      0 |
| Forest             | 0.3299 | 0.1243 |
| Grassland          | 0.0026 |      0 |
| Impervious surface |  0.013 |      0 |
| Shrubland          | 0.0019 |      0 |
| Water body         | 0.3678 | 0.5436 |
| Wetland            |  0.196 | 0.3272 |
