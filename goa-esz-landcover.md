# Deriving Landcover Change Data for Villages Intersecting Goa’s 1 km Eco-Sensitive Zones (ESZ)

<!--LTeX: enabled=false-->

Here’s how I pulled together data on landcover change for villages intersecting the 1 km Eco-Sensitive Zones (ESZ) around Goa’s Protected Areas (PAs). I’ve kept this detailed so it’s easy for you to follow and replicate if needed.

1. Prepping the ESZ and Village Layers

- Eco-Sensitive Zone (ESZ) Buffer:
  - I used the shapefile of Goa’s PAs you shared and created a 1 km buffer around them in QGIS to define the ESZ.
- Village Boundaries:

  - Village boundaries came from the SHRUG database ([ https://www.devdatalab.org/shrug_download/ ]). It’s a curated and consistent dataset with spatially linked Census data with many other fields that may be relevant.

- Using QGIS, from this dataset I selected only those villages that intersected with the ESZs.

2. Moving to Google Earth Engine (GEE)

- I uploaded the ESZ villages shapefile to GEE and used it as the feature collection for querying landcover stats.

3. Landcover Dataset

- The Dataset:

- GLC_FCS30D ([ https://gee-community-catalog.org/projects/glc_fcs/ ]): A global, high-resolution (30m) time-series dataset spanning 1985-2022 with 35 landcover classes.
- You can find the nitty-gritty details in the ESSD paper ([ https://essd.copernicus.org/articles/16/1353/2024/ ]), which also explains the classification hierarchy for aggregating landcover classes.

- Why This Dataset?

- It’s the only continuous 30m-resolution dataset for India, so no other options really.
- That said, take the landcover classifications with a grain of salt—global datasets aren’t always spot-on for local landscapes. In fact, I have found most (other than ESA’s WorldCover) pretty bad.

- Data Characteristics:

- Years: Five-year intervals from 1985 to 2000 (1985, 1990, 1995, 2000), then annual from 2001 to 2022.
- Classes: I used the most detailed landcover classes so you can group them meaningfully later.

4. Zonal Statistics Computation

- What I Did:

- Calculated the area (in hectares) of each landcover class for all ESZ villages over the full time series.

- How It Works:

- I mosaicked the tiled landcover images into single images for each year.
- Then I reclassified the landcover classes for easier analysis.
- Finally, I calculated zonal stats for each village, grouped by landcover class, and exported the results as a CSV.

- Output Details:

- The CSV includes landcover area (in hectares) for each village and year. Fields match the ESZ villages shapefile, so you can easily merge them back for mapping or further analysis.

- Full GEE Code with Comments:

```
{
// Deriving yearly landcover class statistics for villages
// falling in the ESZ of Goa's PAs using the GLC_FCS30D
// landcover dataset from 1985-2022
// https://gee-community-catalog.org/projects/glc_fcs/

// Use GA ESZ villages (based on a 1 km buffer drawn around each PA)
var ga_esz_villages = ee.FeatureCollection('users/mdm/goa_esz_villages');

// Pre-process the Collection
// Yearly data from 2000-2022
var annual = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/annual')
.filterBounds(ga_esz_villages);

// Five-Yearly data for 1985-90, 1990-95 and 1995-2000
var fiveyear = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/five-years-map')
.filterBounds(ga_esz_villages);

// Landcover classification scheme: 36 classes
var classValues = [10, 11, 12, 20, 51, 52, 61, 62, 71, 72, 81, 82, 91, 92, 120, 121, 122, 130, 140, 150, 152, 153, 181, 182, 183, 184, 185, 186, 187, 190, 200, 201, 202, 210, 220, 0];
var classNames = ['Rainfed_cropland', 'Herbaceous_cover_cropland', 'Tree_or_shrub_cover_cropland', ...]; // Full list shortened here for brevity

// Mosaic the data to simplify processing
var annualMosaic = annual.mosaic();
var fiveYearMosaic = fiveyear.mosaic();

// Rename bands to their corresponding years
var yearsList = ee.List.sequence(2000, 2022).map(function(year) {
return ee.Number(year).format('%04d');
});
var fiveYearsList = ee.List.sequence(1985, 1995, 5).map(function(year) {
return ee.Number(year).format('%04d');
});
var annualMosaicRenamed = annualMosaic.rename(yearsList);
var fiveyearMosaicRenamed = fiveYearMosaic.rename(fiveYearsList);

// Combine annual and five-yearly mosaics
var mosaicsCol = ee.ImageCollection.fromImages(
fiveYearsList.map(function(year) {
return fiveyearMosaicRenamed.select([year]).set('year', ee.Number.parse(year));
}).cat(
yearsList.map(function(year) {
return annualMosaicRenamed.select([year]).set('year', ee.Number.parse(year));
})
)
);

// Calculate area by class for each village
var landcoverStats = mosaicsCol.map(function(image) {
return image.reduceRegions({
collection: ga_esz_villages,
reducer: ee.Reducer.sum().group({groupField: 1, groupName: 'class'}),
scale: 30
}).map(function(feature) {
var classAreas = ee.List(feature.get('groups'));
var properties = ee.Dictionary.fromLists(
classNames, classAreas.map(function(item) {return ee.Dictionary(item).get('sum');})
);
return feature.set(properties).set('year', image.get('year'));
});
}).flatten();

// Export the results
Export.table.toDrive({
collection: landcoverStats,
description: 'ga_esz_class_area_by_region_by_year',
fileFormat: 'CSV'
});
}
```

5. Key Takeaways

- The dataset is the best available option but definitely poor—so, please interpret with caution.
- It’s straightforward to reintegrate the CSV with spatial data for visualisation or further analysis in tools like R.
