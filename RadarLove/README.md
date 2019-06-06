# Radar Love

## NOTE: Further development moved to moved to [NightShift](https://github.com/LowellObservatory/NightShift)

Initial experiment to both download and plot NOAA NEXRAD Level II data. Similar rational as [GOESMcGOESface](https://github.com/LowellObservatory/Camelot/tree/master/GOESMcGOESface).

### Dear God Why

All the other examples out there were incomplete or broken!

### Additional Shapefiles

I'm using https://www.naturalearthdata.com/downloads/10m-cultural-vectors/roads/ for
road information, explicitly parsed to only get a subset of road types/categories.

See the ```parseRoads``` function for more details but it's pretty simple using the attributes
in the above mentioned shapefile.
