# LMI McLMIface

A random smattering of tools focused on analysis of images from the
Large Monolithic Imager (LMI) at the Lowell Discovery Telescope (LDT).

Overall status of this: ccdproc is kinda a pain.  I honestly don't know if
this is worth pursuing any further, the API and interface are promising
but I feel like there are still too many weirdnesses.

I have to admit, though, that part of that feeling might be related to
my stubbornness in sticking to the highly abstracted way to allow a
path towards multiamp support at the get-go.

### Dear God Why

Because I want to fiddle around with the latest version of the ccdproc
package, and build up a set of easy-to-use stuff that will eventually land
in another future project.

And, this sort of quick analysis stuff will be helpful for everyone who uses
LMI and will help break us away from both IDL and IRAF ... eventually.
