## GOES Mc GOESface

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
as derived from one or many GOES-16 products.
