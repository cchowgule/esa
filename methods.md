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

fine_mean.loc[('XXX', 'XXX', 0), ['basic_name', 'level_1_name', 'fine_name']] = 'Filled value'

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
| Forest             |  96.72 |
| Water body         |   1.34 |
| Cropland           |   0.85 |
| Wetland            |   0.83 |
| Impervious surface |   0.12 |
| Grassland          |   0.08 |
| Shrubland          |   0.04 |
| Bare areas         |   0.02 |
| Filled value       |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  |  37.05 |
|                    | Evergreen broadleaved forest  |  34.57 |
|                    | Evergreen needleleaved forest |  24.47 |
|                    | Mixed-leaf forest             |   0.61 |
|                    | Deciduous needleleaved forest |   0.02 |
| Water body         | Water body                    |   1.34 |
| Cropland           | Rainfed cropland              |   0.52 |
|                    | Irrigated cropland            |   0.33 |
| Wetland            | Inland wetland                |   0.83 |
|                    | Coastal wetland               |      0 |
| Impervious surface | Impervious surface            |   0.12 |
| Grassland          | Grassland                     |   0.08 |
| Shrubland          | Shrubland                     |   0.04 |
| Bare areas         | Bare areas                    |   0.01 |
|                    | Sparse vegetation             |   0.01 |
| Filled value       | Filled value                  |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  35.08 |
|                    |                               | Closed deciduous broadleaved forest  |   1.97 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  33.41 |
|                    |                               | Closed evergreen broadleaved forest  |   1.16 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  24.43 |
|                    |                               | Closed evergreen needleleaved forest |   0.05 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.61 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |   0.02 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Water body         | Water body                    | Water body                           |   1.34 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   0.42 |
|                    |                               | Herbaceous cover cropland            |    0.1 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.33 |
| Wetland            | Inland wetland                | Flooded flat                         |   0.39 |
|                    |                               | Marsh                                |   0.36 |
|                    |                               | Swamp                                |   0.09 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.12 |
| Grassland          | Grassland                     | Grassland                            |   0.08 |
| Shrubland          | Shrubland                     | Shrubland                            |   0.03 |
|                    | Shrubland                     | Evergreen shrubland                  |   0.02 |
| Bare areas         | Bare areas                    | Bare areas                           |   0.01 |
|                    | Sparse vegetation             | Sparse vegetation                    |   0.01 |
| Filled value       | Filled value                  | Filled value                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 99.52 |
| Cropland           |  0.25 |
| Shrubland          |  0.08 |
| Wetland            |  0.08 |
| Water body         |  0.02 |
| Grassland          |  0.02 |
| Impervious surface |  0.02 |
| Bare areas         |  0.01 |
| Filled value       |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | 76.24 |
|                    | Deciduous broadleaved forest  | 11.52 |
|                    | Evergreen needleleaved forest | 10.44 |
|                    | Mixed-leaf forest             |  1.23 |
|                    | Deciduous needleleaved forest |  0.09 |
| Cropland           | Rainfed cropland              |  0.15 |
|                    | Irrigated cropland            |   0.1 |
| Shrubland          | Shrubland                     |  0.08 |
| Wetland            | Inland wetland                |  0.08 |
|                    | Coastal wetland               |     0 |
| Water body         | Water body                    |  0.02 |
| Grassland          | Grassland                     |  0.02 |
| Impervious surface | Impervious surface            |  0.02 |
| Bare areas         | Sparse vegetation             |  0.01 |
|                    | Bare areas                    |     0 |
| Filled value       | Filled value                  |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 75.82 |
|                    |                               | Closed evergreen broadleaved forest  |  0.43 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    | 10.48 |
|                    |                               | Closed deciduous broadleaved forest  |  1.04 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  10.4 |
|                    |                               | Closed evergreen needleleaved forest |  0.04 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  1.23 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |  0.09 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |  0.11 |
|                    |                               | Herbaceous cover cropland            |  0.04 |
|                    |                               | Tree or shrub cover cropland         |     0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.1 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  0.07 |
|                    |                               | Shrubland                            |     0 |
| Wetland            | Inland wetland                | Marsh                                |  0.04 |
|                    |                               | Swamp                                |  0.03 |
|                    |                               | Flooded flat                         |     0 |
|                    | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
| Water body         | Water body                    | Water body                           |  0.02 |
| Grassland          | Grassland                     | Grassland                            |  0.02 |
| Impervious surface | Impervious surface            | Impervious surface                   |  0.02 |
| Bare areas         | Sparse vegetation             | Sparse vegetation                    |  0.01 |
|                    | Bare areas                    | Bare areas                           |     0 |
| Filled value       | Filled value                  | Filled value                         |     0 |

##### 1 Bhagwan Mahavir WLS

| basic_name         | buffer |
| :----------------- | -----: |
| Forest             |  98.05 |
| Cropland           |   1.01 |
| Grassland          |   0.67 |
| Shrubland          |    0.1 |
| Impervious surface |   0.09 |
| Wetland            |   0.07 |
| Water body         |   0.01 |
| Bare areas         |      0 |
| Filled value       |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  |  44.35 |
|                    | Evergreen needleleaved forest |  38.67 |
|                    | Evergreen broadleaved forest  |  14.98 |
|                    | Mixed-leaf forest             |   0.05 |
|                    | Deciduous needleleaved forest |      0 |
| Cropland           | Rainfed cropland              |   0.57 |
|                    | Irrigated cropland            |   0.44 |
| Grassland          | Grassland                     |   0.67 |
| Shrubland          | Shrubland                     |    0.1 |
| Impervious surface | Impervious surface            |   0.09 |
| Wetland            | Inland wetland                |   0.07 |
|                    | Coastal wetland               |      0 |
| Water body         | Water body                    |   0.01 |
| Bare areas         | Bare areas                    |      0 |
|                    | Sparse vegetation             |      0 |
| Filled value       | Filled value                  |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  43.53 |
|                    |                               | Closed deciduous broadleaved forest  |   0.82 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  38.61 |
|                    |                               | Closed evergreen needleleaved forest |   0.06 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  14.55 |
|                    |                               | Closed evergreen broadleaved forest  |   0.43 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.05 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |      0 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   0.33 |
|                    |                               | Herbaceous cover cropland            |   0.24 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.44 |
| Grassland          | Grassland                     | Grassland                            |   0.67 |
| Shrubland          | Shrubland                     | Shrubland                            |    0.1 |
| Shrubland          |                               | Evergreen shrubland                  |      0 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.09 |
| Wetland            | Inland wetland                | Marsh                                |   0.04 |
|                    |                               | Swamp                                |   0.02 |
|                    |                               | Flooded flat                         |   0.01 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Water body         | Water body                    | Water body                           |   0.01 |
| Bare areas         | Bare areas                    | Bare areas                           |      0 |
|                    | Sparse vegetation             | Sparse vegetation                    |      0 |
| Filled value       | Filled value                  | Filled value                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 99.84 |
| Cropland           |  0.11 |
| Shrubland          |  0.03 |
| Grassland          |  0.02 |
| Impervious surface |     0 |
| Bare areas         |     0 |
| Filled value       |     0 |
| Water body         |     0 |
| Wetland            |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | 77.52 |
|                    | Evergreen needleleaved forest | 14.89 |
|                    | Deciduous broadleaved forest  |  6.42 |
|                    | Mixed-leaf forest             |  0.99 |
|                    | Deciduous needleleaved forest |  0.01 |
| Cropland           | Irrigated cropland            |  0.06 |
|                    | Rainfed cropland              |  0.05 |
| Shrubland          | Shrubland                     |  0.03 |
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
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 77.35 |
|                    |                               | Closed evergreen broadleaved forest  |  0.17 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 14.88 |
|                    |                               | Closed evergreen needleleaved forest |  0.01 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  5.69 |
|                    |                               | Closed deciduous broadleaved forest  |  0.73 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.99 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |  0.01 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Cropland           | Irrigated cropland            | Irrigated cropland                   |  0.06 |
|                    | Rainfed cropland              | Rainfed cropland                     |  0.03 |
|                    |                               | Herbaceous cover cropland            |  0.02 |
|                    |                               | Tree or shrub cover cropland         |     0 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  0.03 |
|                    |                               | Shrubland                            |     0 |
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
| Forest             |  97.39 |
| Cropland           |   1.06 |
| Impervious surface |   0.88 |
| Grassland          |   0.41 |
| Wetland            |   0.14 |
| Water body         |   0.05 |
| Shrubland          |   0.05 |
| Bare areas         |   0.02 |
| Filled value       |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  |  44.12 |
|                    | Evergreen needleleaved forest |  29.33 |
|                    | Evergreen broadleaved forest  |  23.89 |
|                    | Mixed-leaf forest             |   0.05 |
|                    | Deciduous needleleaved forest |   0.01 |
| Cropland           | Irrigated cropland            |   0.57 |
|                    | Rainfed cropland              |   0.49 |
| Impervious surface | Impervious surface            |   0.88 |
| Grassland          | Grassland                     |   0.41 |
| Wetland            | Inland wetland                |   0.14 |
|                    | Coastal wetland               |      0 |
| Water body         | Water body                    |   0.05 |
| Shrubland          | Shrubland                     |   0.05 |
| Bare areas         | Sparse vegetation             |   0.02 |
|                    | Bare areas                    |      0 |
| Filled value       | Filled value                  |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  43.15 |
|                    |                               | Closed deciduous broadleaved forest  |   0.97 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  29.29 |
|                    |                               | Closed evergreen needleleaved forest |   0.04 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  23.52 |
|                    |                               | Closed evergreen broadleaved forest  |   0.37 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.05 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |   0.01 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Cropland           | Irrigated cropland            | Irrigated cropland                   |   0.57 |
|                    | Rainfed cropland              | Rainfed cropland                     |   0.38 |
|                    |                               | Herbaceous cover cropland            |   0.11 |
|                    |                               | Tree or shrub cover cropland         |      0 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.88 |
| Grassland          | Grassland                     | Grassland                            |   0.41 |
| Wetland            | Inland wetland                | Marsh                                |   0.11 |
|                    |                               | Flooded flat                         |   0.02 |
|                    |                               | Swamp                                |   0.01 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Water body         | Water body                    | Water body                           |   0.05 |
| Shrubland          | Shrubland                     | Shrubland                            |   0.05 |
|                    |                               | Evergreen shrubland                  |      0 |
| Bare areas         | Sparse vegetation             | Sparse vegetation                    |   0.02 |
|                    | Bare areas                    | Bare areas                           |      0 |
| Filled value       | Filled value                  | Filled value                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 99.79 |
| Cropland           |  0.12 |
| Grassland          |  0.07 |
| Shrubland          |  0.02 |
| Wetland            |     0 |
| Impervious surface |     0 |
| Bare areas         |     0 |
| Water body         |     0 |
| Filled value       |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  |  82.5 |
|                    | Evergreen needleleaved forest | 12.08 |
|                    | Deciduous broadleaved forest  |  4.81 |
|                    | Mixed-leaf forest             |   0.4 |
|                    | Deciduous needleleaved forest |  0.01 |
| Cropland           | Irrigated cropland            |   0.1 |
|                    | Rainfed cropland              |  0.02 |
| Grassland          | Grassland                     |  0.07 |
| Shrubland          | Shrubland                     |  0.02 |
| Wetland            | Coastal wetland               |     0 |
|                    | Inland wetland                |     0 |
| Impervious surface | Impervious surface            |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |
| Water body         | Water body                    |     0 |
| Filled value       | Filled value                  |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 82.39 |
|                    |                               | Closed evergreen broadleaved forest  |  0.12 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 12.07 |
|                    |                               | Closed evergreen needleleaved forest |  0.01 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  4.12 |
|                    |                               | Closed deciduous broadleaved forest  |  0.69 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.4 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |  0.01 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Cropland           | Irrigated cropland            | Irrigated cropland                   |   0.1 |
|                    | Rainfed cropland              | Rainfed cropland                     |  0.02 |
|                    |                               | Herbaceous cover cropland            |     0 |
|                    |                               | Tree or shrub cover cropland         |     0 |
| Grassland          | Grassland                     | Grassland                            |  0.07 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  0.02 |
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
| Forest             |  95.99 |
| Cropland           |   1.85 |
| Grassland          |   0.96 |
| Water body         |    0.4 |
| Wetland            |   0.37 |
| Shrubland          |   0.19 |
| Impervious surface |   0.19 |
| Bare areas         |   0.04 |
| Filled value       |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  |  66.77 |
|                    | Evergreen needleleaved forest |  24.03 |
|                    | Evergreen broadleaved forest  |   5.14 |
|                    | Mixed-leaf forest             |   0.04 |
|                    | Deciduous needleleaved forest |   0.01 |
| Cropland           | Rainfed cropland              |   1.03 |
|                    | Irrigated cropland            |   0.83 |
| Grassland          | Grassland                     |   0.96 |
| Water body         | Water body                    |    0.4 |
| Wetland            | Inland wetland                |   0.37 |
|                    | Coastal wetland               |      0 |
| Shrubland          | Shrubland                     |   0.19 |
| Impervious surface | Impervious surface            |   0.19 |
| Bare areas         | Sparse vegetation             |   0.03 |
|                    | Bare areas                    |   0.01 |
| Filled value       | Filled value                  |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  65.82 |
|                    |                               | Closed deciduous broadleaved forest  |   0.95 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  23.99 |
|                    |                               | Closed evergreen needleleaved forest |   0.04 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |   4.57 |
|                    |                               | Closed evergreen broadleaved forest  |   0.57 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.04 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |   0.01 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   0.74 |
|                    |                               | Herbaceous cover cropland            |   0.29 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.83 |
| Grassland          | Grassland                     | Grassland                            |   0.96 |
| Water body         | Water body                    | Water body                           |    0.4 |
| Wetland            | Inland wetland                | Marsh                                |   0.19 |
|                    |                               | Flooded flat                         |   0.11 |
|                    |                               | Swamp                                |   0.07 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Shrubland          | Shrubland                     | Shrubland                            |   0.19 |
| Shrubland          |                               | Evergreen shrubland                  |      0 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.19 |
| Bare areas         | Sparse vegetation             | Sparse vegetation                    |   0.03 |
|                    | Bare areas                    | Bare areas                           |   0.01 |
| Filled value       | Filled value                  | Filled value                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 99.63 |
| Cropland           |   0.2 |
| Grassland          |  0.13 |
| Impervious surface |  0.02 |
| Shrubland          |  0.02 |
| Wetland            |  0.01 |
| Bare areas         |     0 |
| Filled value       |     0 |
| Water body         |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen needleleaved forest | 34.39 |
|                    | Evergreen broadleaved forest  | 34.21 |
|                    | Deciduous broadleaved forest  | 30.82 |
|                    | Mixed-leaf forest             |  0.21 |
|                    | Deciduous needleleaved forest |     0 |
| Cropland           | Rainfed cropland              |  0.13 |
|                    | Irrigated cropland            |  0.07 |
| Grassland          | Grassland                     |  0.13 |
| Impervious surface | Impervious surface            |  0.02 |
| Shrubland          | Shrubland                     |  0.02 |
| Wetland            | Inland wetland                |  0.01 |
|                    | Coastal wetland               |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |
| Filled value       | Filled value                  |     0 |
| Water body         | Water body                    |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 34.37 |
|                    |                               | Closed evergreen needleleaved forest |  0.02 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 33.89 |
|                    |                               | Closed evergreen broadleaved forest  |  0.32 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    | 29.96 |
|                    |                               | Closed deciduous broadleaved forest  |  0.86 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.21 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |     0 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Cropland           | Rainfed cropland              | Herbaceous cover cropland            |  0.09 |
|                    |                               | Rainfed cropland                     |  0.04 |
|                    |                               | Tree or shrub cover cropland         |     0 |
|                    | Irrigated cropland            | Irrigated cropland                   |  0.07 |
| Grassland          | Grassland                     | Grassland                            |  0.13 |
| Impervious surface | Impervious surface            | Impervious surface                   |  0.02 |
| Shrubland          | Shrubland                     | Shrubland                            |  0.01 |
|                    |                               | Evergreen shrubland                  |     0 |
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
| Forest             |  99.65 |
| Impervious surface |    0.2 |
| Cropland           |   0.14 |
| Shrubland          |   0.01 |
| Grassland          |   0.01 |
| Wetland            |      0 |
| Bare areas         |      0 |
| Filled value       |      0 |
| Water body         |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Evergreen needleleaved forest |   43.7 |
|                    | Evergreen broadleaved forest  |  36.03 |
|                    | Deciduous broadleaved forest  |  19.42 |
|                    | Mixed-leaf forest             |   0.49 |
|                    | Deciduous needleleaved forest |      0 |
| Impervious surface | Impervious surface            |    0.2 |
| Cropland           | Rainfed cropland              |   0.11 |
|                    | Irrigated cropland            |   0.03 |
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
| Forest             | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  43.67 |
|                    |                               | Closed evergreen needleleaved forest |   0.04 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  35.93 |
|                    |                               | Closed evergreen broadleaved forest  |    0.1 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  18.11 |
|                    |                               | Closed deciduous broadleaved forest  |   1.31 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.49 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |      0 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Impervious surface | Impervious surface            | Impervious surface                   |    0.2 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |    0.1 |
|                    |                               | Herbaceous cover cropland            |   0.01 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.03 |
| Shrubland          | Shrubland                     | Shrubland                            |      0 |
| Shrubland          |                               | Evergreen shrubland                  |      0 |
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
| Cropland           |  0.01 |
| Water body         |     0 |
| Grassland          |     0 |
| Shrubland          |     0 |
| Bare areas         |     0 |
| Filled value       |     0 |
| Impervious surface |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen needleleaved forest | 50.73 |
|                    | Evergreen broadleaved forest  | 40.38 |
|                    | Deciduous broadleaved forest  |  8.69 |
|                    | Mixed-leaf forest             |  0.17 |
|                    | Deciduous needleleaved forest |     0 |
| Wetland            | Inland wetland                |  0.01 |
|                    | Coastal wetland               |     0 |
| Cropland           | Rainfed cropland              |  0.01 |
|                    | Irrigated cropland            |     0 |
| Water body         | Water body                    |     0 |
| Grassland          | Grassland                     |     0 |
| Shrubland          | Shrubland                     |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |
| Filled value       | Filled value                  |     0 |
| Impervious surface | Impervious surface            |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 50.72 |
|                    |                               | Closed evergreen needleleaved forest |  0.02 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 40.32 |
|                    |                               | Closed evergreen broadleaved forest  |  0.07 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  6.62 |
|                    |                               | Closed deciduous broadleaved forest  |  2.07 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.17 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |     0 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Wetland            | Inland wetland                | Swamp                                |  0.01 |
|                    |                               | Marsh                                |     0 |
|                    |                               | Flooded flat                         |     0 |
|                    | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |  0.01 |
|                    |                               | Herbaceous cover cropland            |     0 |
|                    |                               | Tree or shrub cover cropland         |     0 |
|                    | Irrigated cropland            | Irrigated cropland                   |     0 |
| Water body         | Water body                    | Water body                           |     0 |
| Grassland          | Grassland                     | Grassland                            |     0 |
| Shrubland          | Shrubland                     | Shrubland                            |     0 |
|                    |                               | Evergreen shrubland                  |     0 |
| Bare areas         | Bare areas                    | Bare areas                           |     0 |
|                    | Sparse vegetation             | Sparse vegetation                    |     0 |
| Filled value       | Filled value                  | Filled value                         |     0 |
| Impervious surface | Impervious surface            | Impervious surface                   |     0 |

##### 5 Netravali WLS

| basic_name         | buffer |
| :----------------- | -----: |
| Forest             |  81.29 |
| Water body         |  10.94 |
| Wetland            |   4.52 |
| Cropland           |   1.41 |
| Shrubland          |   1.14 |
| Grassland          |   0.61 |
| Bare areas         |   0.04 |
| Impervious surface |   0.03 |
| Filled value       |   0.02 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  |  33.14 |
|                    | Evergreen needleleaved forest |  26.02 |
|                    | Evergreen broadleaved forest  |  21.41 |
|                    | Mixed-leaf forest             |   0.69 |
|                    | Deciduous needleleaved forest |   0.03 |
| Water body         | Water body                    |  10.94 |
| Wetland            | Inland wetland                |   4.52 |
| Wetland            | Coastal wetland               |      0 |
| Cropland           | Rainfed cropland              |   0.83 |
|                    | Irrigated cropland            |   0.58 |
| Shrubland          | Shrubland                     |   1.14 |
| Grassland          | Grassland                     |   0.61 |
| Bare areas         | Bare areas                    |   0.03 |
|                    | Sparse vegetation             |   0.02 |
| Impervious surface | Impervious surface            |   0.03 |
| Filled value       | Filled value                  |   0.02 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  31.18 |
|                    |                               | Closed deciduous broadleaved forest  |   1.97 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  25.96 |
|                    |                               | Closed evergreen needleleaved forest |   0.06 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |  20.74 |
|                    |                               | Closed evergreen broadleaved forest  |   0.67 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.69 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |   0.02 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Water body         | Water body                    | Water body                           |  10.94 |
| Wetland            | Inland wetland                | Flooded flat                         |   3.28 |
|                    |                               | Marsh                                |   1.11 |
|                    |                               | Swamp                                |   0.13 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   0.61 |
|                    |                               | Herbaceous cover cropland            |   0.23 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.58 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |   0.94 |
|                    |                               | Shrubland                            |    0.2 |
| Grassland          | Grassland                     | Grassland                            |   0.61 |
| Bare areas         | Bare areas                    | Bare areas                           |   0.03 |
|                    | Sparse vegetation             | Sparse vegetation                    |   0.02 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.03 |
| Filled value       | Filled value                  | Filled value                         |   0.02 |

| basic_name         |    pa |
| :----------------- | ----: |
| Forest             | 98.03 |
| Shrubland          |   1.5 |
| Cropland           |  0.16 |
| Wetland            |  0.13 |
| Grassland          |  0.11 |
| Water body         |  0.05 |
| Filled value       |  0.01 |
| Impervious surface |     0 |
| Bare areas         |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | 73.96 |
|                    | Evergreen needleleaved forest | 16.12 |
|                    | Deciduous broadleaved forest  |  7.43 |
|                    | Mixed-leaf forest             |  0.49 |
|                    | Deciduous needleleaved forest |  0.03 |
| Shrubland          | Shrubland                     |   1.5 |
| Cropland           | Rainfed cropland              |  0.11 |
|                    | Irrigated cropland            |  0.05 |
| Wetland            | Inland wetland                |  0.13 |
|                    | Coastal wetland               |     0 |
| Grassland          | Grassland                     |  0.11 |
| Water body         | Water body                    |  0.05 |
| Filled value       | Filled value                  |  0.01 |
| Impervious surface | Impervious surface            |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 73.78 |
|                    |                               | Closed evergreen broadleaved forest  |  0.18 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  16.1 |
|                    |                               | Closed evergreen needleleaved forest |  0.02 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  6.28 |
|                    |                               | Closed deciduous broadleaved forest  |  1.15 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.49 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |  0.03 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  1.47 |
|                    |                               | Shrubland                            |  0.03 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |  0.06 |
|                    |                               | Herbaceous cover cropland            |  0.05 |
|                    |                               | Tree or shrub cover cropland         |     0 |
|                    | Irrigated cropland            | Irrigated cropland                   |  0.05 |
| Wetland            | Inland wetland                | Flooded flat                         |  0.08 |
|                    |                               | Marsh                                |  0.04 |
|                    |                               | Swamp                                |  0.01 |
|                    | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
| Grassland          | Grassland                     | Grassland                            |  0.11 |
| Water body         | Water body                    | Water body                           |  0.05 |
| Filled value       | Filled value                  | Filled value                         |  0.01 |
| Impervious surface | Impervious surface            | Impervious surface                   |     0 |
| Bare areas         | Bare areas                    | Bare areas                           |     0 |
|                    | Sparse vegetation             | Sparse vegetation                    |     0 |

##### 6 Cotigaon WLS

| basic_name         | buffer |
| :----------------- | -----: |
| Forest             |   92.6 |
| Cropland           |   5.39 |
| Shrubland          |   1.69 |
| Grassland          |   0.16 |
| Filled value       |    0.1 |
| Impervious surface |   0.05 |
| Bare areas         |      0 |
| Water body         |      0 |
| Wetland            |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Forest             | Evergreen needleleaved forest |  37.03 |
|                    | Deciduous broadleaved forest  |  28.45 |
|                    | Evergreen broadleaved forest  |  25.26 |
|                    | Mixed-leaf forest             |   1.75 |
|                    | Deciduous needleleaved forest |   0.11 |
| Cropland           | Rainfed cropland              |   4.96 |
|                    | Irrigated cropland            |   0.43 |
| Shrubland          | Shrubland                     |   1.69 |
| Grassland          | Grassland                     |   0.16 |
| Filled value       | Filled value                  |    0.1 |
| Impervious surface | Impervious surface            |   0.05 |
| Bare areas         | Bare areas                    |      0 |
|                    | Sparse vegetation             |      0 |
| Water body         | Water body                    |      0 |
| Wetland            | Coastal wetland               |      0 |
|                    | Inland wetland                |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Forest             | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  36.92 |
|                    |                               | Closed evergreen needleleaved forest |   0.11 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  25.53 |
|                    |                               | Closed deciduous broadleaved forest  |   2.92 |
|                    | Evergreen broadleaved forest  | Open evergreen broadleaved forest    |   24.4 |
|                    |                               | Closed evergreen broadleaved forest  |   0.86 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   1.75 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |   0.09 |
|                    |                               | Open deciduous needleleaved forest   |   0.02 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |    2.6 |
|                    |                               | Herbaceous cover cropland            |   2.11 |
|                    |                               | Tree or shrub cover cropland         |   0.26 |
|                    | Irrigated cropland            | Irrigated cropland                   |   0.43 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |   1.64 |
|                    |                               | Shrubland                            |   0.05 |
| Grassland          | Grassland                     | Grassland                            |   0.16 |
| Filled value       | Filled value                  | Filled value                         |    0.1 |
| Impervious surface | Impervious surface            | Impervious surface                   |   0.05 |
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
| Forest             | 97.66 |
| Shrubland          |  1.65 |
| Cropland           |  0.54 |
| Filled value       |  0.14 |
| Impervious surface |     0 |
| Grassland          |     0 |
| Bare areas         |     0 |
| Water body         |     0 |
| Wetland            |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | 69.26 |
|                    | Evergreen needleleaved forest | 18.92 |
|                    | Deciduous broadleaved forest  |  8.46 |
|                    | Mixed-leaf forest             |  0.97 |
|                    | Deciduous needleleaved forest |  0.05 |
| Shrubland          | Shrubland                     |  1.65 |
| Cropland           | Rainfed cropland              |  0.52 |
|                    | Irrigated cropland            |  0.02 |
| Filled value       | Filled value                  |  0.14 |
| Impervious surface | Impervious surface            |     0 |
| Grassland          | Grassland                     |     0 |
| Bare areas         | Bare areas                    |     0 |
|                    | Sparse vegetation             |     0 |
| Water body         | Water body                    |     0 |
| Wetland            | Coastal wetland               |     0 |
|                    | Inland wetland                |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 69.06 |
|                    |                               | Closed evergreen broadleaved forest  |  0.21 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   | 18.88 |
|                    |                               | Closed evergreen needleleaved forest |  0.03 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  6.72 |
|                    |                               | Closed deciduous broadleaved forest  |  1.74 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |  0.97 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |  0.03 |
|                    |                               | Open deciduous needleleaved forest   |  0.02 |
| Shrubland          | Shrubland                     | Evergreen shrubland                  |  1.65 |
|                    |                               | Shrubland                            |     0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |  0.34 |
|                    |                               | Herbaceous cover cropland            |  0.13 |
|                    |                               | Tree or shrub cover cropland         |  0.05 |
|                    | Irrigated cropland            | Irrigated cropland                   |  0.02 |
| Filled value       | Filled value                  | Filled value                         |  0.14 |
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
| Water body         |  36.78 |
| Forest             |  32.99 |
| Wetland            |   19.6 |
| Cropland           |   8.75 |
| Impervious surface |    1.3 |
| Grassland          |   0.26 |
| Shrubland          |   0.19 |
| Bare areas         |   0.13 |
| Filled value       |      0 |

| basic_name         | level_1_name                  | buffer |
| :----------------- | :---------------------------- | -----: |
| Water body         | Water body                    |  36.78 |
| Forest             | Deciduous broadleaved forest  |  30.39 |
|                    | Evergreen broadleaved forest  |   1.31 |
|                    | Evergreen needleleaved forest |   1.21 |
|                    | Mixed-leaf forest             |   0.07 |
|                    | Deciduous needleleaved forest |   0.01 |
| Wetland            | Inland wetland                |  19.59 |
|                    | Coastal wetland               |   0.01 |
| Cropland           | Rainfed cropland              |   5.14 |
|                    | Irrigated cropland            |   3.61 |
| Impervious surface | Impervious surface            |    1.3 |
| Grassland          | Grassland                     |   0.26 |
| Shrubland          | Shrubland                     |   0.19 |
| Bare areas         | Bare areas                    |   0.08 |
|                    | Sparse vegetation             |   0.05 |
| Filled value       | Filled value                  |      0 |

| basic_name         | level_1_name                  | fine_name                            | buffer |
| :----------------- | :---------------------------- | :----------------------------------- | -----: |
| Water body         | Water body                    | Water body                           |  36.78 |
| Forest             | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  29.87 |
|                    |                               | Closed deciduous broadleaved forest  |   0.52 |
|                    | Evergreen broadleaved forest  | Closed evergreen broadleaved forest  |   0.66 |
|                    |                               | Open evergreen broadleaved forest    |   0.65 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |   1.18 |
|                    |                               | Closed evergreen needleleaved forest |   0.03 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |   0.07 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |   0.01 |
|                    |                               | Open deciduous needleleaved forest   |      0 |
| Wetland            | Inland wetland                | Marsh                                |  11.11 |
|                    |                               | Flooded flat                         |   4.64 |
|                    |                               | Swamp                                |   3.85 |
|                    | Coastal wetland               | Mangrove                             |      0 |
|                    |                               | Tidal flat                           |      0 |
| Cropland           | Rainfed cropland              | Rainfed cropland                     |   4.97 |
|                    |                               | Herbaceous cover cropland            |   0.17 |
|                    |                               | Tree or shrub cover cropland         |      0 |
|                    | Irrigated cropland            | Irrigated cropland                   |   3.61 |
| Impervious surface | Impervious surface            | Impervious surface                   |    1.3 |
| Grassland          | Grassland                     | Grassland                            |   0.26 |
| Shrubland          | Shrubland                     | Shrubland                            |   0.19 |
|                    |                               | Evergreen shrubland                  |      0 |
| Bare areas         | Bare areas                    | Bare areas                           |   0.08 |
|                    | Sparse vegetation             | Sparse vegetation                    |   0.05 |
| Filled value       | Filled value                  | Filled value                         |      0 |

| basic_name         |    pa |
| :----------------- | ----: |
| Water body         | 54.36 |
| Wetland            | 32.72 |
| Forest             | 12.43 |
| Cropland           |  0.42 |
| Bare areas         |  0.07 |
| Grassland          |     0 |
| Filled value       |     0 |
| Shrubland          |     0 |
| Impervious surface |     0 |

| basic_name         | level_1_name                  |    pa |
| :----------------- | :---------------------------- | ----: |
| Water body         | Water body                    | 54.36 |
| Wetland            | Inland wetland                | 32.72 |
|                    | Coastal wetland               |     0 |
| Forest             | Evergreen broadleaved forest  | 12.32 |
|                    | Deciduous broadleaved forest  |  0.08 |
|                    | Evergreen needleleaved forest |  0.03 |
|                    | Deciduous needleleaved forest |     0 |
|                    | Mixed-leaf forest             |     0 |
| Cropland           | Irrigated cropland            |  0.41 |
|                    | Rainfed cropland              |  0.01 |
| Bare areas         | Sparse vegetation             |  0.07 |
|                    | Bare areas                    |     0 |
| Grassland          | Grassland                     |     0 |
| Filled value       | Filled value                  |     0 |
| Shrubland          | Shrubland                     |     0 |
| Impervious surface | Impervious surface            |     0 |

| basic_name         | level_1_name                  | fine_name                            |    pa |
| :----------------- | :---------------------------- | :----------------------------------- | ----: |
| Water body         | Water body                    | Water body                           | 54.36 |
| Wetland            | Inland wetland                | Swamp                                | 17.44 |
|                    |                               | Marsh                                | 11.17 |
|                    |                               | Flooded flat                         |  4.11 |
|                    | Coastal wetland               | Mangrove                             |     0 |
|                    |                               | Tidal flat                           |     0 |
| Forest             | Evergreen broadleaved forest  | Open evergreen broadleaved forest    | 12.32 |
|                    |                               | Closed evergreen broadleaved forest  |     0 |
|                    | Deciduous broadleaved forest  | Open deciduous broadleaved forest    |  0.08 |
|                    |                               | Closed deciduous broadleaved forest  |     0 |
|                    | Evergreen needleleaved forest | Open evergreen needleleaved forest   |  0.03 |
|                    |                               | Closed evergreen needleleaved forest |     0 |
|                    | Deciduous needleleaved forest | Closed deciduous needleleaved forest |     0 |
|                    |                               | Open deciduous needleleaved forest   |     0 |
|                    | Mixed-leaf forest             | Closed mixed-leaf forest             |     0 |
| Cropland           | Irrigated cropland            | Irrigated cropland                   |  0.41 |
|                    | Rainfed cropland              | Rainfed cropland                     |  0.01 |
|                    |                               | Herbaceous cover cropland            |     0 |
|                    |                               | Tree or shrub cover cropland         |     0 |
| Bare areas         | Sparse vegetation             | Sparse vegetation                    |  0.07 |
|                    | Bare areas                    | Bare areas                           |     0 |
| Grassland          | Grassland                     | Grassland                            |     0 |
| Filled value       | Filled value                  | Filled value                         |     0 |
| Shrubland          | Shrubland                     | Shrubland                            |     0 |
|                    |                               | Evergreen shrubland                  |     0 |
| Impervious surface | Impervious surface            | Impervious surface                   |     0 |

### 2 - Percentage change in land-cover over time
