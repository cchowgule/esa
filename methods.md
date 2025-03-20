# Data preparation methods

The following data preparation was done in Python using the following packages and libraries:

- geopandas
- matplotlib

I used the interactive shell IPython as it allows for a richer visual experience and provides methods for previewing maps and graphs.

## 1 - Protected area, buffer & village polygons

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
In [1]: import geopandas as gp

In [2]: pas = gp.read_file('data/Goa_protected_areas/Notified_PA_Goa.shp')

In [3]: pas.columns.to_list()
Out[3]: ['Shape_Leng', 'Shape_Area', 'Name', 'geometry']

In [5]: pas = pas.drop(columns=['Shape_Leng', 'Shape_Area'])

In [6]: pas.Name
```

In order to consistently reference a single polygon the "Name" column of the dataset needs to be unique.

```
In [7]: pas = pas.rename(columns={'Name': 'name'})

In [8]: pas = pas.reset_index()

In [9]: pas['index'] = pas['index'].astype(str)

In [10]: pas['name'] = pas['index'] + '_' + pas['name'].str.replace(' ', '_').str.replace('.', '')

In [11]: pas.name
```

Since all the areas of interest lie within the state of Goa, I have chosen to use the coordinate reference system [EPSG:7779](https://spatialreference.org/ref/epsg/7779/).

The "geometry" column represents the boundaries of the PAs not including the 1,000 m buffers. Therefore, the buffers would be the set of polygons extending from the current geometry columns outward 1,000 m. The polygons include a Z axis which is not relevant for the current analysis.

```
In [12]: pas = pas.rename(columns={'geometry': 'pa'})

In [13]: pas['pa'] = pas['pa'].force_2d()

In [14]: pas = pas.set_geometry('pa')

In [15]: pas = pas.to_crs('EPSG:7779')

In [16]: pas['buffer'] = pas['pa'].buffer(1000)

In [17]: pas['buffer'] = pas['buffer'].difference(pas['pa'])
```

The buffers constructed above do not take into account the fact that most of the PAs are contiguous and along Goa's eastern border. The buffers overlap each other, other PAs or fall outside the state. They need to be clipped account for these inconsistencies.

The state's boundaries are taken from [the SHRUG](https://www.devdatalab.org/shrug) and preprocessed to include only the polygon representing Goa in the correct CRS.

```
In [17]: state = gp.read_feather('feathers/admin_units/state.feather')

In [18]: state.index.names

In [19]: state.columns.to_list()

In [20]: pas['buffer'] = pas['buffer'].intersection(state.loc['30', 'geometry'])

In [21]: pa_polygon_list = pas['pa'].to_list()

In [22]: for pa_polygon in pa_polygon_list:
     ...:     pas['buffer'] = pas['buffer'].difference(pa_polygon)
```

**ISSUE** The buffers also intersect with themselves. For any analysis done on a per PA basis this will not have an impact. However, any analysis done on a state-wide basis will include some double counting for the area within the intersection of the buffers.

Mapping these polygons give the follwing state-wide and per PA maps.

```
In [23]: import matplotlib.pyplot as plt

In [24]: fig, ax = plt.subplots(layout="tight", num='State-wide')

In [25]: plt.axis('off')

In [26]: state.plot(ax=ax, linewidth=0.5, ec="grey", fc="none", linestyle="--")

In [27]: ax.annotate(text='Goa', xy=state.loc['30'].geometry.representative_point().coords[0], ha="center", wrap=True, color="grey", fontsize='medium')

In [28]: pas['pa'].plot(ax=ax, fc='none', ec='green', hatch="///")

In [29]: pas['buffer'].plot(ax=ax, fc='none', ec='yellow', hatch="///")

In [30]: def add_names(row):
    ...:     text = ' '.join(row['name'].split('_')[1:])
    ...:     pa = gp.GeoSeries(row.pa)
    ...:     rep_point = pa.representative_point().get_coordinates().values[0]
    ...:     ax.annotate(
    ...:         text=text,
    ...:         xy=(rep_point[0], rep_point[1]),
    ...:         ha="center",
    ...:         wrap=True,
    ...:         color="green",
    ...:         fontsize="medium",
    ...:     )

In [31]: pas.apply(add_names, axis=1)

In [32]: fig.savefig('state_wide_pas_buffers.png', dpi=150, format="png", bbox_inches="tight")
```

![State-wide PAs & buffers](pngs/state_wide_pas_buffers.png)
