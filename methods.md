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

In order to consistently reference a single polygon the "Name" column of the dataset needs to be unique.

Since all the areas of interest lie within the state of Goa, I have chosen to use the coordinate reference system [EPSG:7779](https://spatialreference.org/ref/epsg/7779/).

The "geometry" column represents the boundaries of the PAs not including the 1,000 m buffers. Therefore, the buffers would be the set of polygons extending from the current geometry columns outward 1,000 m. The polygons include a Z axis which is not relevant for the current analysis.

These buffers do not take into account the fact that most of the PAs are contiguous and along Goa's eastern border. The buffers overlap each other, other PAs or fall outside the state. They need to be clipped to account for these inconsistencies.

The state's boundaries are taken from [the SHRUG](https://www.devdatalab.org/shrug) and preprocessed to include only the polygon representing Goa and have been reprojected into [EPSG:7779](https://spatialreference.org/ref/epsg/7779/).

This data set is saved as "eszs.feather".

```
import geopandas as gp

pas = gp.read_file('data/Goa_protected_areas/Notified_PA_Goa.shp')

pas = pas.drop(columns=['Shape_Leng', 'Shape_Area'])

pas = pas.rename(columns={'Name': 'name'})

# Use index values to make ESZ names unique
pas = pas.reset_index()

pas['index'] = pas['index'].astype(str)

pas['name'] = pas['index'] + '_' + pas['name'].str.replace(' ', '_').str.replace('.', '')

# Drop old index column
pas = pas.drop(columns=['index'])

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
import geopandas as gp

import pandas as pd

# Read in data
pas = gp.read_feather('feathers/eszs.feather')

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
import geopandas as gp

import matplotlib.pyplot as plt

# Read in data
state = gp.read_feather('feathers/admin_units/state.feather')

clipped_villages = gp.read_feather('feathers/clipped_villages.feather')

pas = gp.read_feather('feathers/eszs.feather')

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
# fig.savefig('pngs/maps/state_wide_pas_buffers.png', dpi=150, format='png', bbox_inches='tight')

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
#     fig.savefig('pngs/maps/' + fig.get_label() + '.png', dpi=150, format='png', bbox_inches='tight')
```

![State-wide PAs & buffers](pngs/maps/state_wide_pas_buffers.png)
![Mhadei WLS PA](pngs/maps/0_Mhadei_WLS_PA.png)
![Mhadei WLS buffer](pngs/maps/0_Mhadei_WLS_buffer.png)
![Bhagwan Mahavir (N) WLS PA](pngs/maps/1_Bhagwan_Mahavir_WLS_PA.png)
![Bhagwan Mahavir (N) WLS buffer](pngs/maps/1_Bhagwan_Mahavir_WLS_buffer.png)
![Mollem NP PA](pngs/maps/2_Mollem_NP_PA.png)
![Mollem NP buffer](pngs/maps/2_Mollem_NP_buffer.png)
![Bhagwan Mahavir (S) WLS PA](pngs/maps/3_Bhagwan_Mahavir_WLS_PA.png)
![Bhagwan Mahavir (S) WLS buffer](pngs/maps/3_Bhagwan_Mahavir_WLS_buffer.png)
![Bondla WLS PA](pngs/maps/4_Bondla_WLS_PA.png)
![Bondla WLS buffer](pngs/maps/4_Bondla_WLS_buffer.png)
![Netravali WLS PA](pngs/maps/5_Netravali_WLS_PA.png)
![Netravali WLS buffer](pngs/maps/5_Netravali_WLS_buffer.png)
![Cotigaon WLS PA](pngs/maps/6_Cotigaon_WLS_PA.png)
![Cotigaon WLS buffer](pngs/maps/6_Cotigaon_WLS_buffer.png)
![Dr Salim Ali WLS PA](pngs/maps/7_Dr_Salim_Ali_WLS_PA.png)
![Dr Salim Ali WLS buffer](pngs/maps/7_Dr_Salim_Ali_WLS_buffer.png)

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
import geopandas as gp

import ee

import geemap as gm

import pandas as pd

import datetime as dt

# Read in data
clipped_villages = gp.read_feather('feathers/clipped_villages.feather')

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
lc_data_df = lc_data_df.fillna(0)

# Separate annual and five-yearly data
annual = lc_data_df.loc[lc_data_df.index.get_level_values('year') > dt.datetime(2000,1,1)]

five_year = lc_data_df.loc[lc_data_df.index.get_level_values('year') <= dt.datetime(2000,1,1)]

# Resample five-yearly data to annual
idx_names = list(five_year.index.names)

resampled = five_year.reset_index(idx_names[:-1]).groupby(idx_names[:-1], group_keys=False).resample('YS').first()

# Forward fill new data
resampled = resampled.ffill()

# Reset index
resampled = resampled.reset_index().set_index(idx_names)

# Combine annual and resampled data
lc_data_df = pd.concat([resampled, annual])

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

**ISSUE** It would be better to interpolate the new rows instead of just forward filling them. When I tried the land-cover and polygon areas no longer matched. I need to look closer at the different interpolation strategies available.

There are a total of 247 admin. units in the clipped_villages dataset. Each village should be represented by a set of rows for each year between 1985 and 2022 inclusive. The land_cover_frequency and land_cover_area datasets contain exactly: 247 x 38 = 9,386 rows of data indicating they are valid for the timeseries in question.

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

On average this difference represents less than 0.001% of the area of the admin. unit, granted with a significant variability in the statistic, an indication of a reasonably good fit between land-cover area and actual area.

## Data analysis methods

### 1 - Average percentage land-cover types

Certain land-cover types cover a significantly greater proportion of both the PAs and buffers. Average percentage values over the entire dataset aggregated to each land-cover type level show which types predominate in each PA and buffer.

Apart from Dr. Salim Ali WLS, which has significant water bodies and wetlands, the ESZs are dominated by forest land-cover types in both their PAs and buffers. Cotigaon and Dr. Salim Ali WLS are the only ESZs to show more than ~1% cropland types in their buffers.

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

fine_mean.loc[('XXX', 'XXX', '0'), ['basic_name', 'level_1_name', 'fine_name']] = 'Filled value'

fine_mean = fine_mean.set_index(['basic_name', 'level_1_name', 'fine_name'])

# Aggregate means by land-cover aggregation levels
level_1_mean = fine_mean.groupby(['basic_name', 'level_1_name']).sum()

basic_mean = fine_mean.groupby(['basic_name']).sum()

eszs = list(set(x[0] for x in fine_mean.columns.to_list()))

eszs.sort()

# Print Markdown tables of basic classification types for each ESZ
for e in eszs:
     b_df_buffer = basic_mean[e]['buffer'].mul(100).sort_values(ascending=False).round(2)
     l_idx_buffer = [l for b in b_df_buffer.index.to_list() for l in level_1_mean.index.to_list() if l[0] == b]
     l_df_buffer = level_1_mean[e]['buffer'].reindex(l_idx_buffer).mul(100).round(2).groupby(level='basic_name', sort=False).apply(lambda x: x.sort_values(ascending=False)).droplevel(0)
     f_idx_buffer = [f for l in l_df_buffer.index.to_list() for f in fine_mean.index.to_list() if f[:2] == l]
     f_df_buffer = fine_mean[e]['buffer'].reindex(f_idx_buffer).mul(100).round(2).groupby(level=['basic_name', 'level_1_name'], sort=False).apply(lambda x: x.sort_values(ascending=False)).droplevel([0, 1])
     b_df_pa = basic_mean[e]['pa'].mul(100).sort_values(ascending=False).round(2)
     l_idx_pa = [l for b in b_df_pa.index.to_list() for l in level_1_mean.index.to_list() if l[0] == b]
     l_df_pa = level_1_mean[e]['pa'].reindex(l_idx_pa).mul(100).round(2).groupby(level='basic_name', sort=False).apply(lambda x: x.sort_values(ascending=False)).droplevel(0)
     f_idx_pa = [f for l in l_df_pa.index.to_list() for f in fine_mean.index.to_list() if f[:2] == l]
     f_df_pa = fine_mean[e]['pa'].reindex(f_idx_pa).mul(100).round(2).groupby(level=['basic_name', 'level_1_name'], sort=False).apply(lambda x: x.sort_values(ascending=False)).droplevel([0, 1])
     print()
     print(e.replace('_', ' '))
     print()
     print(b_df_buffer.reset_index().to_markdown(index=False))
     print()
     print(l_df_buffer.reset_index().to_markdown(index=False))
     print()
     print(f_df_buffer.reset_index().to_markdown(index=False))
     print()
     print(b_df_pa.reset_index().to_markdown(index=False))
     print()
     print(l_df_pa.reset_index().to_markdown(index=False))
     print()
     print(f_df_pa.reset_index().to_markdown(index=False))
     print()

# Uncomment below to save mean datasets
# fine_mean.to_feather('feathers/fine_mean.feather')
# level_1_mean.to_feather('feathers/level_1_mean.feather')
# basic_mean.to_feather('feathers/basic_mean.feather')
```

##### 0 Mhadei WLS

| basic_name         | buffer |
| :----------------- | -----: |
| Forest             |  96.69 |
| Water body         |    1.3 |
| Cropland           |   0.87 |
| Wetland            |   0.86 |
| Impervious surface |    0.1 |
| Grassland          |   0.09 |
| Shrubland          |   0.08 |
| Bare areas         |   0.01 |
| Filled value       |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  |  35.36 |
|                    | Evergreen broadleaved forest  |  33.98 |
|                    | Evergreen needleleaved forest |  26.92 |
|                    | Mixed-leaf forest             |   0.42 |
|                    | Deciduous needleleaved forest |   0.01 |
| Water body         | Water body                    |    1.3 |
| Cropland           | Rainfed cropland              |   0.54 |
|                    | Irrigated cropland            |   0.34 |
| Wetland            | Inland wetland                |   0.86 |
|                    | Coastal wetland               |      0 |
| Impervious surface | Impervious surface            |    0.1 |
| Grassland          | Grassland                     |   0.09 |
| Shrubland          | Shrubland                     |   0.08 |
| Bare areas         | Bare areas                    |   0.01 |
|                    | Sparse vegetation             |   0.01 |
| Filled value       | Filled value                  |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  33.97 |
|                    |                               | Closed deciduous broadleaved forest  |   1.39 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  33.19 |
|                    |                               | Closed evergreen broadleaved forest  |   0.79 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  26.89 |
|                    |                               | Closed evergreen needleleaved forest |   0.03 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.42 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |   0.01 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Water body         | Water body                    | Water body                           |    1.3 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   0.44 |
|                    |                               | Herbaceous cover cropland            |    0.1 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.34 |
| Wetland            | Inland wetland                | Flooded flat                         |   0.48 |
|                    |                               | Marsh                                |   0.31 |
|                    |                               | Swamp                                |   0.07 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Impervious surface | Impervious surface            | Impervious surface                   |    0.1 |
| Grassland          | Grassland                     | Grassland                            |   0.09 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |   0.04 |
|                    |                               | Shrubland                            |   0.03 |
| Bare areas         | Bare areas                    | Bare areas                           |   0.01 |
|                    | Sparse vegetation             | Sparse vegetation                    |   0.01 |
| Filled value       | Filled value                  | Filled value                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 99.35 |
| Cropland           |  0.25 |
| Shrubland          |  0.25 |
| Wetland            |  0.07 |
| Grassland          |  0.03 |
| Water body         |  0.02 |
| Impervious surface |  0.02 |
| Bare areas         |  0.01 |
| Filled value       |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | 76.25 |
|                    | Evergreen needleleaved forest | 11.44 |
|                    | Deciduous broadleaved forest  | 10.76 |
|                    | Mixed-leaf forest             |  0.84 |
|                    | Deciduous needleleaved forest |  0.06 |
| Cropland           | Rainfed cropland              |  0.15 |
|                    | Irrigated cropland            |   0.1 |
| Shrubland          | Shrubland                     |  0.25 |
| Wetland            | Inland wetland                |  0.07 |
|                    | Coastal wetland               |     0 |
| Grassland          | Grassland                     |  0.03 |
| Water body         | Water body                    |  0.02 |
| Impervious surface | Impervious surface            |  0.02 |
| Bare areas         | Sparse vegetation             |  0.01 |
|                    | Bare areas                    |     0 |
| Filled value       | Filled value                  |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 75.95 |
|                    |                               | Closed evergreen broadleaved forest  |  0.29 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 11.41 |
|                    |                               | Closed evergreen needleleaved forest |  0.03 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    | 10.04 |
|                    |                               | Closed deciduous broadleaved forest  |  0.72 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.84 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |  0.06 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |  0.11 |
|                    |                               | Herbaceous cover cropland            |  0.04 |
|                    |                               | Tree or shrub cover cropland         |     0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.1 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  0.25 |
|                    |                               | Shrubland                            |     0 |
| Wetland            | Inland wetland                | Marsh                                |  0.04 |
|                    |                               | Swamp                                |  0.03 |
|                    |                               | Flooded flat                         |  0.01 |
|                    | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
| Grassland          | Grassland                     | Grassland                            |  0.03 |
| Water body         | Water body                    | Water body                           |  0.02 |
| Impervious surface | Impervious surface            | Impervious surface                   |  0.02 |
| Bare areas         | Sparse vegetation             | Sparse vegetation                    |  0.01 |
|                    | Bare areas                    | Bare areas                           |     0 |
| Filled value       | Filled value                  | Filled value                         |     0 |

##### 1 Bhagwan Mahavir WLS

| basic_name         | buffer |
| :----------------- | -----: |
| Forest             |  98.26 |
| Cropland           |   0.94 |
| Grassland          |   0.59 |
| Shrubland          |   0.08 |
| Impervious surface |   0.06 |
| Wetland            |   0.06 |
| Water body         |   0.01 |
| Bare areas         |      0 |
| Filled value       |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  |  43.31 |
|                    | Evergreen needleleaved forest |  40.33 |
|                    | Evergreen broadleaved forest  |  14.58 |
|                    | Mixed-leaf forest             |   0.03 |
|                    | Deciduous needleleaved forest |      0 |
| Cropland           | Rainfed cropland              |   0.53 |
|                    | Irrigated cropland            |   0.41 |
| Grassland          | Grassland                     |   0.59 |
| Shrubland          | Shrubland                     |   0.08 |
| Impervious surface | Impervious surface            |   0.06 |
| Wetland            | Inland wetland                |   0.06 |
|                    | Coastal wetland               |      0 |
| Water body         | Water body                    |   0.01 |
| Bare areas         | Bare areas                    |      0 |
|                    | Sparse vegetation             |      0 |
| Filled value       | Filled value                  |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  42.71 |
|                    |                               | Closed deciduous broadleaved forest  |   0.61 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  40.29 |
|                    |                               | Closed evergreen needleleaved forest |   0.04 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  14.29 |
|                    |                               | Closed evergreen broadleaved forest  |   0.29 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.03 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |      0 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   0.34 |
|                    |                               | Herbaceous cover cropland            |   0.19 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.41 |
| Grassland          | Grassland                     | Grassland                            |   0.59 |
| Shrubland          | Shrubland                     | Shrubland                            |   0.08 |
|                    |                               | Evergreen shrubland                  |      0 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.06 |
| Wetland            | Inland wetland                | Marsh                                |   0.03 |
|                    |                               | Swamp                                |   0.02 |
|                    |                               | Flooded flat                         |   0.02 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Water body         | Water body                    | Water body                           |   0.01 |
| Bare areas         | Bare areas                    | Bare areas                           |      0 |
|                    | Sparse vegetation             | Sparse vegetation                    |      0 |
| Filled value       | Filled value                  | Filled value                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 99.77 |
| Shrubland          |  0.11 |
| Cropland           |   0.1 |
| Grassland          |  0.02 |
| Impervious surface |     0 |
| Bare areas         |     0 |
| Filled value       |     0 |
| Water body         |     0 |
| Wetland            |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | 77.34 |
|                    | Evergreen needleleaved forest | 15.92 |
|                    | Deciduous broadleaved forest  |  5.82 |
|                    | Mixed-leaf forest             |  0.68 |
|                    | Deciduous needleleaved forest |  0.01 |
| Shrubland          | Shrubland                     |  0.11 |
| Cropland           | Irrigated cropland            |  0.05 |
|                    | Rainfed cropland              |  0.05 |
| Grassland          | Grassland                     |  0.02 |
| Impervious surface | Impervious surface            |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |
| Filled value       | Filled value                  |     0 |
| Water body         | Water body                    |     0 |
| Wetland            | Coastal wetland               |     0 |
|                    | Inland wetland                |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 77.22 |
|                    |                               | Closed evergreen broadleaved forest  |  0.12 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 15.91 |
|                    |                               | Closed evergreen needleleaved forest |  0.01 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  5.32 |
|                    |                               | Closed deciduous broadleaved forest  |   0.5 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.68 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |  0.01 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  0.11 |
|                    |                               | Shrubland                            |     0 |
| Cropland           | Irrigated cropland            | Irrigated cropland                   |  0.05 |
|                    | Rainfed cropland              | Rainfed cropland                     |  0.03 |
|                    |                               | Herbaceous cover cropland            |  0.02 |
|                    |                               | Tree or shrub cover cropland         |     0 |
| Grassland          | Grassland                     | Grassland                            |  0.02 |
| Impervious surface | Impervious surface            | Impervious surface                   |     0 |
| Bare areas         | Bare areas                    | Bare areas                           |     0 |
|                    | Sparse vegetation             | Sparse vegetation                    |     0 |
| Filled value       | Filled value                  | Filled value                         |     0 |
| Water body         | Water body                    | Water body                           |     0 |
| Wetland            | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
|                    | Inland wetland                | Swamp                                |     0 |
|                    |                               | Marsh                                |     0 |
|                    |                               | Flooded flat                         |     0 |

##### 2 Mollem NP

| basic_name         | buffer |
| :----------------- | -----: |
| Forest             |  97.57 |
| Cropland           |   1.14 |
| Impervious surface |   0.69 |
| Grassland          |   0.41 |
| Wetland            |   0.11 |
| Shrubland          |   0.04 |
| Water body         |   0.03 |
| Bare areas         |   0.01 |
| Filled value       |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  |  43.64 |
|                    | Evergreen needleleaved forest |  30.21 |
|                    | Evergreen broadleaved forest  |  23.67 |
|                    | Mixed-leaf forest             |   0.04 |
|                    | Deciduous needleleaved forest |      0 |
| Cropland           | Irrigated cropland            |   0.67 |
|                    | Rainfed cropland              |   0.48 |
| Impervious surface | Impervious surface            |   0.69 |
| Grassland          | Grassland                     |   0.41 |
| Wetland            | Inland wetland                |   0.11 |
|                    | Coastal wetland               |      0 |
| Shrubland          | Shrubland                     |   0.04 |
| Water body         | Water body                    |   0.03 |
| Bare areas         | Sparse vegetation             |   0.01 |
|                    | Bare areas                    |      0 |
| Filled value       | Filled value                  |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  42.91 |
|                    |                               | Closed deciduous broadleaved forest  |   0.74 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  30.18 |
|                    |                               | Closed evergreen needleleaved forest |   0.03 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  23.42 |
|                    |                               | Closed evergreen broadleaved forest  |   0.25 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.04 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |      0 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Cropland           | Irrigated cropland            | Irrigated cropland                   |   0.67 |
|                    | Rainfed cropland              | Tree or shrub cover cropland         |      0 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.69 |
| Grassland          | Grassland                     | Grassland                            |   0.41 |
| Wetland            | Inland wetland                | Marsh                                |   0.09 |
|                    |                               | Flooded flat                         |   0.02 |
|                    |                               | Swamp                                |   0.01 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Shrubland          | Shrubland                     | Shrubland                            |   0.04 |
|                    |                               | Evergreen shrubland                  |      0 |
| Water body         | Water body                    | Water body                           |   0.03 |
| Bare areas         | Sparse vegetation             | Sparse vegetation                    |   0.01 |
|                    | Bare areas                    | Bare areas                           |      0 |
| Filled value       | Filled value                  | Filled value                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 99.76 |
| Cropland           |   0.1 |
| Grassland          |  0.08 |
| Shrubland          |  0.06 |
| Wetland            |     0 |
| Impervious surface |     0 |
| Bare areas         |     0 |
| Water body         |     0 |
| Filled value       |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | 82.66 |
|                    | Evergreen needleleaved forest | 12.59 |
|                    | Deciduous broadleaved forest  |  4.25 |
|                    | Mixed-leaf forest             |  0.27 |
|                    | Deciduous needleleaved forest |     0 |
| Cropland           | Irrigated cropland            |  0.08 |
|                    | Rainfed cropland              |  0.02 |
| Grassland          | Grassland                     |  0.08 |
| Shrubland          | Shrubland                     |  0.06 |
| Wetland            | Coastal wetland               |     0 |
|                    | Inland wetland                |     0 |
| Impervious surface | Impervious surface            |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |
| Water body         | Water body                    |     0 |
| Filled value       | Filled value                  |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 82.58 |
|                    |                               | Closed evergreen broadleaved forest  |  0.08 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 12.58 |
|                    |                               | Closed evergreen needleleaved forest |  0.01 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  3.77 |
|                    |                               | Closed deciduous broadleaved forest  |  0.48 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.27 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |     0 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Cropland           | Irrigated cropland            | Irrigated cropland                   |  0.08 |
|                    | Rainfed cropland              | Rainfed cropland                     |  0.02 |
|                    |                               | Herbaceous cover cropland            |     0 |
|                    |                               | Tree or shrub cover cropland         |     0 |
| Grassland          | Grassland                     | Grassland                            |  0.08 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  0.05 |
|                    |                               | Shrubland                            |     0 |
| Wetland            | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
|                    | Inland wetland                | Swamp                                |     0 |
|                    |                               | Marsh                                |     0 |
|                    |                               | Flooded flat                         |     0 |
| Impervious surface | Impervious surface            | Impervious surface                   |     0 |
| Bare areas         | Bare areas                    | Bare areas                           |     0 |
|                    | Sparse vegetation             | Sparse vegetation                    |     0 |
| Water body         | Water body                    | Water body                           |     0 |
| Filled value       | Filled value                  | Filled value                         |     0 |

##### 3 Bhagwan Mahavir WLS

| basic_name         | buffer |
| :----------------- | -----: |
| Forest             |  96.44 |
| Cropland           |   1.82 |
| Grassland          |   0.83 |
| Wetland            |   0.28 |
| Water body         |   0.28 |
| Shrubland          |   0.17 |
| Impervious surface |   0.14 |
| Bare areas         |   0.03 |
| Filled value       |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  |  66.64 |
|                    | Evergreen needleleaved forest |     25 |
|                    | Evergreen broadleaved forest  |   4.76 |
|                    | Mixed-leaf forest             |   0.03 |
|                    | Deciduous needleleaved forest |      0 |
| Cropland           | Rainfed cropland              |   0.92 |
|                    | Irrigated cropland            |    0.9 |
| Grassland          | Grassland                     |   0.83 |
| Wetland            | Inland wetland                |   0.28 |
|                    | Coastal wetland               |      0 |
| Water body         | Water body                    |   0.28 |
| Shrubland          | Shrubland                     |   0.17 |
| Impervious surface | Impervious surface            |   0.14 |
| Bare areas         | Sparse vegetation             |   0.02 |
|                    | Bare areas                    |   0.01 |
| Filled value       | Filled value                  |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  65.97 |
|                    |                               | Closed deciduous broadleaved forest  |   0.68 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  24.98 |
|                    |                               | Closed evergreen needleleaved forest |   0.03 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |   4.37 |
|                    |                               | Closed evergreen broadleaved forest  |   0.39 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.03 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |      0 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   0.69 |
|                    |                               | Herbaceous cover cropland            |   0.23 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |    0.9 |
| Grassland          | Grassland                     | Grassland                            |   0.83 |
| Wetland            | Inland wetland                | Marsh                                |   0.15 |
|                    |                               | Flooded flat                         |   0.08 |
|                    |                               | Swamp                                |   0.06 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Water body         | Water body                    | Water body                           |   0.28 |
| Shrubland          | Shrubland                     | Shrubland                            |   0.17 |
|                    |                               | Evergreen shrubland                  |      0 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.14 |
| Bare areas         | Sparse vegetation             | Sparse vegetation                    |   0.02 |
|                    | Bare areas                    | Bare areas                           |   0.01 |
| Filled value       | Filled value                  | Filled value                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 99.63 |
| Cropland           |  0.19 |
| Grassland          |  0.13 |
| Shrubland          |  0.03 |
| Impervious surface |  0.01 |
| Wetland            |  0.01 |
| Bare areas         |     0 |
| Filled value       |     0 |
| Water body         |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen needleleaved forest | 35.35 |
|                    | Evergreen broadleaved forest  | 34.07 |
|                    | Deciduous broadleaved forest  | 30.06 |
|                    | Mixed-leaf forest             |  0.14 |
|                    | Deciduous needleleaved forest |     0 |
| Cropland           | Rainfed cropland              |  0.13 |
|                    | Irrigated cropland            |  0.07 |
| Grassland          | Grassland                     |  0.13 |
| Shrubland          | Shrubland                     |  0.03 |
| Impervious surface | Impervious surface            |  0.01 |
| Wetland            | Inland wetland                |  0.01 |
|                    | Coastal wetland               |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |
| Filled value       | Filled value                  |     0 |
| Water body         | Water body                    |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 35.34 |
|                    |                               | Closed evergreen needleleaved forest |  0.01 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 33.85 |
|                    |                               | Closed evergreen broadleaved forest  |  0.22 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    | 29.47 |
|                    |                               | Closed deciduous broadleaved forest  |  0.59 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.14 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |     0 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Cropland           | Rainfed cropland              | Herbaceous cover cropland            |  0.08 |
|                    |                               | Rainfed cropland                     |  0.04 |
|                    |                               | Tree or shrub cover cropland         |     0 |
|                    | Irrigated cropland            | Irrigated cropland                   |  0.07 |
| Grassland          | Grassland                     | Grassland                            |  0.13 |
| Shrubland          | Shrubland                     | Shrubland                            |  0.02 |
|                    |                               | Evergreen shrubland                  |     0 |
| Impervious surface | Impervious surface            | Impervious surface                   |  0.01 |
| Wetland            | Inland wetland                | Marsh                                |  0.01 |
|                    |                               | Swamp                                |     0 |
|                    |                               | Flooded flat                         |     0 |
|                    | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
| Bare areas         | Bare areas                    | Bare areas                           |     0 |
|                    | Sparse vegetation             | Sparse vegetation                    |     0 |
| Filled value       | Filled value                  | Filled value                         |     0 |
| Water body         | Water body                    | Water body                           |     0 |

##### 4 Bondla WLS

| basic_name         | buffer |
| :----------------- | -----: |
| Forest             |  99.69 |
| Impervious surface |   0.18 |
| Cropland           |   0.11 |
| Shrubland          |   0.01 |
| Grassland          |   0.01 |
| Wetland            |      0 |
| Bare areas         |      0 |
| Filled value       |      0 |
| Water body         |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Evergreen needleleaved forest |  45.35 |
|                    | Evergreen broadleaved forest  |  35.47 |
|                    | Deciduous broadleaved forest  |  18.53 |
|                    | Mixed-leaf forest             |   0.34 |
|                    | Deciduous needleleaved forest |      0 |
| Impervious surface | Impervious surface            |   0.18 |
| Cropland           | Rainfed cropland              |   0.09 |
|                    | Irrigated cropland            |   0.02 |
| Shrubland          | Shrubland                     |   0.01 |
| Grassland          | Grassland                     |   0.01 |
| Wetland            | Coastal wetland               |      0 |
|                    | Inland wetland                |      0 |
| Bare areas         | Bare areas                    |      0 |
|                    | Sparse vegetation             |      0 |
| Filled value       | Filled value                  |      0 |
| Water body         | Water body                    |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  45.32 |
|                    |                               | Closed evergreen needleleaved forest |   0.02 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  35.41 |
|                    |                               | Closed evergreen broadleaved forest  |   0.07 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  17.62 |
|                    |                               | Closed deciduous broadleaved forest  |   0.91 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.34 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |      0 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.18 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   0.08 |
|                    |                               | Herbaceous cover cropland            |   0.01 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.02 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |   0.01 |
|                    | Shrubland                     | Shrubland                            |      0 |
| Grassland          | Grassland                     | Grassland                            |   0.01 |
| Wetland            | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
|                    | Inland wetland                | Swamp                                |      0 |
|                    |                               | Marsh                                |      0 |
|                    |                               | Flooded flat                         |      0 |
| Bare areas         | Bare areas                    | Bare areas                           |      0 |
|                    | Sparse vegetation             | Sparse vegetation                    |      0 |
| Filled value       | Filled value                  | Filled value                         |      0 |
| Water body         | Water body                    | Water body                           |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 99.97 |
| Wetland            |  0.01 |
| Shrubland          |  0.01 |
| Cropland           |     0 |
| Water body         |     0 |
| Grassland          |     0 |
| Bare areas         |     0 |
| Filled value       |     0 |
| Impervious surface |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen needleleaved forest | 51.98 |
|                    | Evergreen broadleaved forest  | 40.46 |
|                    | Deciduous broadleaved forest  |  7.42 |
|                    | Mixed-leaf forest             |  0.11 |
|                    | Deciduous needleleaved forest |     0 |
| Wetland            | Inland wetland                |  0.01 |
|                    | Coastal wetland               |     0 |
| Shrubland          | Shrubland                     |  0.01 |
| Cropland           | Irrigated cropland            |     0 |
|                    | Rainfed cropland              |     0 |
| Water body         | Water body                    |     0 |
| Grassland          | Grassland                     |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |
| Filled value       | Filled value                  |     0 |
| Impervious surface | Impervious surface            |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 51.97 |
|                    |                               | Closed evergreen needleleaved forest |  0.01 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 40.42 |
|                    |                               | Closed evergreen broadleaved forest  |  0.04 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |     6 |
|                    |                               | Closed deciduous broadleaved forest  |  1.42 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.11 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |     0 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Wetland            | Inland wetland                | Swamp                                |  0.01 |
|                    |                               | Marsh                                |     0 |
|                    |                               | Flooded flat                         |     0 |
|                    | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  0.01 |
|                    |                               | Shrubland                            |     0 |
| Cropland           | Irrigated cropland            | Irrigated cropland                   |     0 |
|                    | Rainfed cropland              | Rainfed cropland                     |     0 |
|                    |                               | Herbaceous cover cropland            |     0 |
|                    |                               | Tree or shrub cover cropland         |     0 |
| Water body         | Water body                    | Water body                           |     0 |
| Grassland          | Grassland                     | Grassland                            |     0 |
| Bare areas         | Bare areas                    | Bare areas                           |     0 |
|                    | Sparse vegetation             | Sparse vegetation                    |     0 |
| Filled value       | Filled value                  | Filled value                         |     0 |
| Impervious surface | Impervious surface            | Impervious surface                   |     0 |

##### 5 Netravali WLS

| basic_name         | buffer |
| :----------------- | -----: |
| Forest             |  82.09 |
| Water body         |  10.51 |
| Wetland            |   4.41 |
| Cropland           |   1.24 |
| Shrubland          |   1.16 |
| Grassland          |   0.53 |
| Bare areas         |   0.03 |
| Impervious surface |   0.02 |
| Filled value       |   0.01 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  |  32.55 |
|                    | Evergreen needleleaved forest |  28.03 |
|                    | Evergreen broadleaved forest  |  21.03 |
|                    | Mixed-leaf forest             |   0.47 |
|                    | Deciduous needleleaved forest |   0.02 |
| Water body         | Water body                    |  10.51 |
| Wetland            | Inland wetland                |   4.41 |
|                    | Coastal wetland               |      0 |
| Cropland           | Rainfed cropland              |   0.69 |
|                    | Irrigated cropland            |   0.56 |
| Shrubland          | Shrubland                     |   1.16 |
| Grassland          | Grassland                     |   0.53 |
| Bare areas         | Bare areas                    |   0.02 |
|                    | Sparse vegetation             |   0.01 |
| Impervious surface | Impervious surface            |   0.02 |
| Filled value       | Filled value                  |   0.01 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  31.07 |
|                    |                               | Closed deciduous broadleaved forest  |   1.48 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  27.98 |
|                    |                               | Closed evergreen needleleaved forest |   0.04 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  20.57 |
|                    |                               | Closed evergreen broadleaved forest  |   0.46 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.47 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |   0.02 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Water body         | Water body                    | Water body                           |  10.51 |
| Wetland            | Inland wetland                | Flooded flat                         |   3.04 |
|                    |                               | Marsh                                |   1.25 |
|                    |                               | Swamp                                |   0.12 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |    0.5 |
|                    |                               | Herbaceous cover cropland            |   0.18 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.56 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |   0.99 |
|                    |                               | Shrubland                            |   0.16 |
| Grassland          | Grassland                     | Grassland                            |   0.53 |
| Bare areas         | Bare areas                    | Bare areas                           |   0.02 |
|                    | Sparse vegetation             | Sparse vegetation                    |   0.01 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.02 |
| Filled value       | Filled value                  | Filled value                         |   0.01 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 98.05 |
| Shrubland          |  1.54 |
| Cropland           |  0.14 |
| Wetland            |  0.11 |
| Grassland          |  0.09 |
| Water body         |  0.05 |
| Filled value       |  0.01 |
| Impervious surface |     0 |
| Bare areas         |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | 74.17 |
|                    | Evergreen needleleaved forest | 16.93 |
|                    | Deciduous broadleaved forest  |  6.61 |
|                    | Mixed-leaf forest             |  0.33 |
|                    | Deciduous needleleaved forest |  0.02 |
| Shrubland          | Shrubland                     |  1.54 |
| Cropland           | Rainfed cropland              |   0.1 |
|                    | Irrigated cropland            |  0.04 |
| Wetland            | Inland wetland                |  0.11 |
|                    | Coastal wetland               |     0 |
| Grassland          | Grassland                     |  0.09 |
| Water body         | Water body                    |  0.05 |
| Filled value       | Filled value                  |  0.01 |
| Impervious surface | Impervious surface            |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 74.04 |
|                    |                               | Closed evergreen broadleaved forest  |  0.12 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 16.91 |
|                    |                               | Closed evergreen needleleaved forest |  0.02 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |   5.8 |
|                    |                               | Closed deciduous broadleaved forest  |  0.81 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.33 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |  0.02 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  1.51 |
|                    |                               | Shrubland                            |  0.03 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |  0.05 |
|                    |                               | Herbaceous cover cropland            |  0.04 |
|                    |                               | Tree or shrub cover cropland         |     0 |
|                    | Irrigated cropland            | Irrigated cropland                   |  0.04 |
| Wetland            | Inland wetland                | Flooded flat                         |  0.07 |
|                    |                               | Marsh                                |  0.04 |
|                    |                               | Swamp                                |  0.01 |
|                    | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
| Grassland          | Grassland                     | Grassland                            |  0.09 |
| Water body         | Water body                    | Water body                           |  0.05 |
| Filled value       | Filled value                  | Filled value                         |  0.01 |
| Impervious surface | Impervious surface            | Impervious surface                   |     0 |
| Bare areas         | Bare areas                    | Bare areas                           |     0 |
|                    | Sparse vegetation             | Sparse vegetation                    |     0 |

##### 6 Cotigaon WLS

| basic_name         | buffer |
| :----------------- | -----: |
| Forest             |  92.59 |
| Cropland           |   5.16 |
| Shrubland          |   1.97 |
| Grassland          |   0.17 |
| Filled value       |   0.07 |
| Impervious surface |   0.04 |
| Bare areas         |      0 |
| Water body         |      0 |
| Wetland            |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Evergreen needleleaved forest |  39.32 |
|                    | Deciduous broadleaved forest  |  26.78 |
|                    | Evergreen broadleaved forest  |  25.23 |
|                    | Mixed-leaf forest             |    1.2 |
|                    | Deciduous needleleaved forest |   0.07 |
| Cropland           | Rainfed cropland              |   4.77 |
|                    | Irrigated cropland            |   0.39 |
| Shrubland          | Shrubland                     |   1.97 |
| Grassland          | Grassland                     |   0.17 |
| Filled value       | Filled value                  |   0.07 |
| Impervious surface | Impervious surface            |   0.04 |
| Bare areas         | Bare areas                    |      0 |
|                    | Sparse vegetation             |      0 |
| Water body         | Water body                    |      0 |
| Wetland            | Coastal wetland               |      0 |
|                    | Inland wetland                |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  39.24 |
|                    |                               | Closed evergreen needleleaved forest |   0.08 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  24.77 |
|                    |                               | Closed deciduous broadleaved forest  |   2.01 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  24.64 |
|                    |                               | Closed evergreen broadleaved forest  |   0.59 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |    1.2 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |   0.06 |
|                    |                               | Open deciduous needleleaved forest   |   0.01 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   2.63 |
|                    |                               | Herbaceous cover cropland            |   1.89 |
|                    |                               | Tree or shrub cover cropland         |   0.26 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.39 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |    1.9 |
|                    |                               | Shrubland                            |   0.07 |
| Grassland          | Grassland                     | Grassland                            |   0.17 |
| Filled value       | Filled value                  | Filled value                         |   0.07 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.04 |
| Bare areas         | Bare areas                    | Bare areas                           |      0 |
|                    | Sparse vegetation             | Sparse vegetation                    |      0 |
| Water body         | Water body                    | Water body                           |      0 |
| Wetland            | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
|                    | Inland wetland                | Swamp                                |      0 |
|                    |                               | Marsh                                |      0 |
|                    |                               | Flooded flat                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 97.64 |
| Shrubland          |  1.75 |
| Cropland           |   0.5 |
| Filled value       |   0.1 |
| Impervious surface |     0 |
| Grassland          |     0 |
| Bare areas         |     0 |
| Water body         |     0 |
| Wetland            |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | 69.42 |
|                    | Evergreen needleleaved forest | 19.97 |
|                    | Deciduous broadleaved forest  |  7.55 |
|                    | Mixed-leaf forest             |  0.66 |
|                    | Deciduous needleleaved forest |  0.04 |
| Shrubland          | Shrubland                     |  1.75 |
| Cropland           | Rainfed cropland              |  0.49 |
|                    | Irrigated cropland            |  0.02 |
| Filled value       | Filled value                  |   0.1 |
| Impervious surface | Impervious surface            |     0 |
| Grassland          | Grassland                     |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |
| Water body         | Water body                    |     0 |
| Wetland            | Coastal wetland               |     0 |
|                    | Inland wetland                |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 69.28 |
|                    |                               | Closed evergreen broadleaved forest  |  0.14 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 19.95 |
|                    |                               | Closed evergreen needleleaved forest |  0.02 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  6.36 |
|                    |                               | Closed deciduous broadleaved forest  |  1.19 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.66 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |  0.02 |
|                    |                               | Open deciduous needleleaved forest   |  0.02 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  1.75 |
|                    |                               | Shrubland                            |  0.01 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |  0.32 |
|                    |                               | Herbaceous cover cropland            |  0.12 |
|                    |                               | Tree or shrub cover cropland         |  0.05 |
|                    | Irrigated cropland            | Irrigated cropland                   |  0.02 |
| Filled value       | Filled value                  | Filled value                         |   0.1 |
| Impervious surface | Impervious surface            | Impervious surface                   |     0 |
| Grassland          | Grassland                     | Grassland                            |     0 |
| Bare areas         | Bare areas                    | Bare areas                           |     0 |
|                    | Sparse vegetation             | Sparse vegetation                    |     0 |
| Water body         | Water body                    | Water body                           |     0 |
| Wetland            | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
|                    | Inland wetland                | Swamp                                |     0 |
|                    |                               | Marsh                                |     0 |
|                    |                               | Flooded flat                         |     0 |

##### 7 Dr Salim Ali WLS

| basic_name         | buffer |
| :----------------- | -----: |
| Water body         |   37.1 |
| Forest             |  33.15 |
| Wetland            |  19.55 |
| Cropland           |   8.54 |
| Impervious surface |   0.92 |
| Shrubland          |   0.36 |
| Grassland          |    0.3 |
| Bare areas         |   0.09 |
| Filled value       |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Water body         | Water body                    |   37.1 |
| Forest             | Deciduous broadleaved forest  |  30.73 |
|                    | Evergreen needleleaved forest |   1.24 |
|                    | Evergreen broadleaved forest  |   1.14 |
|                    | Mixed-leaf forest             |   0.05 |
|                    | Deciduous needleleaved forest |   0.01 |
| Wetland            | Inland wetland                |  19.54 |
|                    | Coastal wetland               |   0.01 |
| Cropland           | Rainfed cropland              |   5.22 |
|                    | Irrigated cropland            |   3.32 |
| Impervious surface | Impervious surface            |   0.92 |
| Shrubland          | Shrubland                     |   0.36 |
| Grassland          | Grassland                     |    0.3 |
| Bare areas         | Bare areas                    |   0.05 |
|                    | Sparse vegetation             |   0.04 |
| Filled value       | Filled value                  |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Water body         | Water body                    | Water body                           |   37.1 |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  30.24 |
|                    | Deciduous broadleaved forest  | Closed deciduous broadleaved forest  |   0.48 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |   1.21 |
|                    | Evergreen needleleaved forest | Closed evergreen needleleaved forest |   0.02 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |   0.69 |
|                    | Evergreen broadleaved forest  | Closed evergreen broadleaved forest  |   0.45 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.05 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |   0.01 |
|                    | Deciduous needleleaved forest | Open deciduous needleleaved forest   |      0 |
| Wetland            | Inland wetland                | Marsh                                |   9.15 |
|                    | Inland wetland                | Flooded flat                         |    6.8 |
|                    | Inland wetland                | Swamp                                |   3.59 |
|                    | Coastal wetland               | Mangrove                             |   0.01 |
|                    | Coastal wetland               | Tidal flat                           |      0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   5.05 |
|                    | Rainfed cropland              | Herbaceous cover cropland            |   0.16 |
|                    | Rainfed cropland              | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   3.32 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.92 |
| Shrubland          | Shrubland                     | Shrubland                            |   0.36 |
|                    | Shrubland                     | Evergreen shrubland                  |      0 |
| Grassland          | Grassland                     | Grassland                            |    0.3 |
| Bare areas         | Bare areas                    | Bare areas                           |   0.05 |
|                    | Sparse vegetation             | Sparse vegetation                    |   0.04 |
| Filled value       | Filled value                  | Filled value                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Water body         |  56.5 |
| Wetland            | 31.71 |
| Forest             |  11.4 |
| Cropland           |  0.34 |
| Bare areas         |  0.05 |
| Grassland          |     0 |
| Filled value       |     0 |
| Shrubland          |     0 |
| Impervious surface |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Water body         | Water body                    |  56.5 |
| Wetland            | Inland wetland                | 31.71 |
|                    | Coastal wetland               |     0 |
| Forest             | Evergreen broadleaved forest  | 11.33 |
|                    | Deciduous broadleaved forest  |  0.05 |
|                    | Evergreen needleleaved forest |  0.02 |
|                    | Deciduous needleleaved forest |     0 |
|                    | Mixed-leaf forest             |     0 |
| Cropland           | Irrigated cropland            |  0.33 |
|                    | Rainfed cropland              |  0.01 |
| Bare areas         | Sparse vegetation             |  0.05 |
|                    | Bare areas                    |     0 |
| Grassland          | Grassland                     |     0 |
| Filled value       | Filled value                  |     0 |
| Shrubland          | Shrubland                     |     0 |
| Impervious surface | Impervious surface            |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Water body         | Water body                    | Water body                           |  56.5 |
| Wetland            | Inland wetland                | Swamp                                | 16.67 |
|                    |                               | Marsh                                |   9.7 |
|                    |                               | Flooded flat                         |  5.34 |
|                    | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 11.33 |
|                    |                               | Closed evergreen broadleaved forest  |     0 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  0.05 |
|                    |                               | Closed deciduous broadleaved forest  |     0 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  0.02 |
|                    |                               | Closed evergreen needleleaved forest |     0 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |     0 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |     0 |
| Cropland           | Irrigated cropland            | Irrigated cropland                   |  0.33 |
|                    | Rainfed cropland              | Rainfed cropland                     |  0.01 |
|                    |                               | Herbaceous cover cropland            |     0 |
|                    |                               | Tree or shrub cover cropland         |     0 |
| Bare areas         | Sparse vegetation             | Sparse vegetation                    |  0.05 |
|                    | Bare areas                    | Bare areas                           |     0 |
| Grassland          | Grassland                     | Grassland                            |     0 |
| Filled value       | Filled value                  | Filled value                         |     0 |
| Shrubland          | Shrubland                     | Shrubland                            |     0 |
|                    |                               | Evergreen shrubland                  |     0 |
| Impervious surface | Impervious surface            | Impervious surface                   |     0 |

### 2 - Land-cover over time

It seems to me, based on the relative proportions of each land-cover type in the tables above, that level 1 and fine types do not provide much more insight than the basic types. Therefore, when graphing changes in land-cover over time I am aggregating the types up to the basic classification system.

In order to compare the changes between different land-cover types the graphs show the cumulative change in hectares from the earliest data year (1985).

```
import pandas as pd

import matplotlib.pyplot as plt

import datetime as dt

# Read in the data
land_cover_area = pd.read_feather('feathers/land_cover_area.feather')

land_cover_types = pd.read_feather('feathers/GLC_FCS30D_landcover_types.feather')

# Aggregate the data along both axes
land_cover_area = land_cover_area.groupby(['esz', 'part', 'year']).sum()

land_cover_area = land_cover_area.T.groupby('basic_id').sum().T

# Convert sq. m to ha
land_cover_area /= 10000

# Get basic classification names and colours for graph legends
lc_names = land_cover_types.groupby('basic_id')['basic_classification_system'].first().to_dict()

lc_names['XXX'] = 'Filled value'

lc_colors = land_cover_types.groupby('basic_classification_system')['basic_color'].first().to_dict()

lc_colors = {k : tuple([float(x)/255 for x in v]) for k, v in lc_colors.items()}

lc_colors['Filled value'] = (0.0, 0.0, 0.0)

# Group by ESZ and part for individual plots
lc_area_grouped = land_cover_area.groupby(['esz', 'part'], as_index=False, group_keys=False)

# Loop over ESZ parts
figs = []

for name, group in lc_area_grouped:
       name_parts = name[0].split('_') + [name[1]]
       # Difference of row n from n - 1
       # Drop data pre 2000
       # Cumulative sum of differences
       group_cum_diff = group.loc[group.index.get_level_values('year') >= dt.datetime(2000,1,1)].diff().cumsum().fillna(0)
       # Rename IDs to basic classification system names
       new_names = {k : v for k, v in lc_names.items() if k in group_cum_diff.columns.to_list()}
       group_cum_diff = group_cum_diff.rename(columns=new_names)
       # Get dictionary of colours matched to names
       group_colors = {k : v for k, v in lc_colors.items() if k in group_cum_diff.columns.to_list()}
       fig, ax = plt.subplots(num='_'.join(name_parts))
       # Set y-axis to years
       # Plot
       group_cum_diff.reset_index(list(group_cum_diff.index.names)[:-1]).plot.line(ax=ax, color=group_colors, linewidth=3)
       # Set legend position and shape
       ax.legend(title='Basic land-cover types', loc='lower center', ncols=len(new_names))
       # Set axis positions, formats and titles
       plt.title(' '.join([p for p in name_parts if p != 'pa'] + ['PA' for p in name_parts if p == 'pa']))
       plt.ylabel('Cumulative difference (ha)')
       ax.spines['bottom'].set_position('zero')
       ax.spines['top'].set_color('none')
       ax.spines['right'].set_color('none')
       figs.append(fig)

# Uncomment below to save all individual PA and buffer graphs
# for fig in figs:
#     fig.savefig('pngs/graphs/' + fig.get_label() + '.png', dpi=150, format='png', bbox_inches='tight')
```

**QUESTION** Are the strong correlations between changes in certain pairs of land-cover types actually representative of changes on the ground? Or are they the result of ambiguity in the identification model?

![Mhadei WLS buffer](pngs/graphs/0_Mhadei_WLS_buffer.png)
![Mhadei WLS PA](pngs/graphs/0_Mhadei_WLS_pa.png)
![Bhagwan Mahavir (N) WLS buffer](pngs/graphs/1_Bhagwan_Mahavir_WLS_buffer.png)
![Bhagwan Mahavir (N) WLS PA](pngs/graphs/1_Bhagwan_Mahavir_WLS_pa.png)
![Mollem NP buffer](pngs/graphs/2_Mollem_NP_buffer.png)
![Mollem NP PA](pngs/graphs/2_Mollem_NP_pa.png)
![Bhagwan Mahavir (S) WLS buffer](pngs/graphs/3_Bhagwan_Mahavir_WLS_buffer.png)
![Bhagwan Mahavir (S) WLS PA](pngs/graphs/3_Bhagwan_Mahavir_WLS_pa.png)
![Bondla WLS buffer](pngs/graphs/4_Bondla_WLS_buffer.png)
![Bondla WLS PA](pngs/graphs/4_Bondla_WLS_pa.png)
![Netravali WLS buffer](pngs/graphs/5_Netravali_WLS_buffer.png)
![Netravali WLS PA](pngs/graphs/5_Netravali_WLS_pa.png)
![Cotigaon WLS buffer](pngs/graphs/6_Cotigaon_WLS_buffer.png)
![Cotigaon WLS PA](pngs/graphs/6_Cotigaon_WLS_pa.png)
![Dr Salim Ali WLS buffer](pngs/graphs/7_Dr_Salim_Ali_WLS_buffer.png)
![Dr Salim Ali WLS PA](pngs/graphs/7_Dr_Salim_Ali_WLS_pa.png)
