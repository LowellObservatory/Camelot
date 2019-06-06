# Bokeh McBokehface

## NOTE: Further development moved to moved to [NightShift](https://github.com/LowellObservatory/NightShift)

Experiment to figure out the deployment and setup details of a bokeh-server instance
that serves multiple plots, and has a single/unified database query that gets
distributed to all of them.

### Dear God Why

The bokeh docs are pretty bad, sadly.  Most of what I could find was specific to bokeh versions at or near 0.11 or 0.12,
where this was built using bokeh version 1.2.0.  There also weren't many/any details on streaming to a 
ColumnDataSource, or for a way to pass data to the plot endpoints from a single point.  And the callback details
were sketchy at best.  So, this experimental repository was where all the bugs got worked out.
