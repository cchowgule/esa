# The plan

<!--LTeX: enabled=false-->

- Figure out the reducer on GEE
- Filtering on bounds works fine, gets rectangle

Let's start with some basic stats:

- Group by village code, across time series
  - Graph change in cover types
  - Display by village all cover types change over time
  - 1 graph for aggregated state-wise data
  - Using pandas how do we display this?

## Questions

- What else do we need?
- What are meaningful landcover class groupings?

## Possibilities

- Display graphs over actual maps for interactivity

## Test for plotly

{% include_relative plotly_graph.html %}

## Coordinate reference system

I am using EPSG:7779 as it is localised to Goa and our area of interest is so small.
