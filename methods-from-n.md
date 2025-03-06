# Methods: Spatial Analysis of Landcover Change in Goa's Eco-Sensitive Zones

## Study Area Delineation

Eco-Sensitive Zones (ESZs) were delineated by creating 1-kilometer buffers around Goa's Protected Areas (PAs) using QGIS. Village boundaries were obtained from the Socioeconomic High-resolution Rural-Urban Geographic Platform (SHRUG) database, which provides spatially linked census data. Villages intersecting with the ESZs were selected using spatial analysis in QGIS to create the final study area boundary.

## Landcover Change Analysis

Landcover change analysis was conducted using the Global Land Cover time-series dataset (GLC_FCS30D), accessed through Google Earth Engine (GEE). This dataset provides 30-meter resolution landcover classifications from 1985 to 2022, with 35 distinct landcover classes. Temporal coverage includes five-year intervals from 1985 to 2000 (1985, 1990, 1995, 2000), followed by annual data from 2001 to 2022.

The GLC_FCS30D dataset was selected as it represents the only continuous 30-meter resolution dataset available for the study region. While global datasets may have limitations in local-scale accuracy, this dataset provided the necessary temporal and spatial resolution for the analysis. The most detailed landcover classification scheme was retained to enable flexible aggregation of classes during subsequent analysis.

## Data Processing

The analysis workflow consisted of:
1. Generation of ESZ buffers from PA boundaries
2. Selection of intersecting villages from the SHRUG database
3. Upload of the resulting village boundary dataset to GEE as a feature collection
4. Extraction of landcover statistics for the study area using the GLC_FCS30D dataset

## Data Limitations

It is important to note that while global landcover products provide valuable temporal coverage, they may not capture local landscape characteristics with the same accuracy as region-specific classifications. This limitation should be considered when interpreting fine-scale landcover changes within the study area.
