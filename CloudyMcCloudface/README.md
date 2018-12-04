## Cloudy Mc Cloudface

Experiment to assess the sky background in an all sky camera image.

An initial experiment to see if it's possible to construct a simple/single
metric that can be plotted/assessed and see if it's a "good" or "bad" night.

The initially committed version operates on differential image pairs; I found
this gave the best comprimise between dealing with the full moon and showing
what is actually going on in the sky.

It accepts a simple image mask which will remove stuff on the horizon
and/or your telescope structure.  Without this, I found that there were
a lot of glints and spikes from the structure(s) reflecting moonlight.

The mask was constructed in GIMP, and is a simple multiplicative mask.
That means that black (==0) areas are removed, and white (==255) areas are kept
as-is in the images.  The mask is really threshold filtered just after
reading it in, so anything with a value > 200 will be treated as "white"
and kept; this keeps worries about compression slightly at bay, though
I admit it could be done cleaner with a different approach.

I included a batch of 50 raw files to play with, taken near/at full Moon and
with a patch of clouds passing by.  Should be good to experiment/hack on.

### Dear God Why

Because an observatory almost always has one of these, but they're hit
or miss on whether they share/explain their analysis of said images.

Let's be open, fellow observatory people!
