# GOES Mc GOESface

## NOTE: Further development moved to moved to [NightShift](https://github.com/LowellObservatory/NightShift)

Experiment to grab the latest and greatest GOES-16 data from an AWS bucket
and manipulate it/plot it ourselves to see if it's fast enough for 
nighttime TO/DCT observer usage.

### Dear God Why

Because most GOES-16 sites you can find via google don't want you either
hotlinking or script downloading their data.  Ignoring those cries for mercy
and doing it anyways means that whatever we build might eventually go away some day,
and then some poor soul has to redo it or find a new website to reap.  This is
in theory the better way to do things, even if it means a little extra work.

And, by doing it ourselves, we can do value-added things like
put markers on the various observing sites way more precisely
or even start to fiddle with statistics over the observing sites
as derived from one or many GOES-16 products, or do simple
manipulation (subtraction, RGB combos, etc.) ourselves to really 
get the best thing we think we need.

Grabbing data from AWS (or wherever) also puts us in a nice position
to use other open/public datasets hosted by any of the various "big data"
groups for Earth/environmental science, too.

### Additional Shapefiles

I'm using https://www.naturalearthdata.com/downloads/10m-cultural-vectors/roads/ for 
road information, explicitly parsed to only get a subset of road types/categories. 

See the ```parseRoads``` function for more details but it's pretty simple using the attributes
in the above mentioned shapefile.

### Additional datasets

[AWS NOAA NEXRAD](https://registry.opendata.aws/noaa-nexrad/)
